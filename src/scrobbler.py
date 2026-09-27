import json
import time
from dataclasses import dataclass
from queue import SimpleQueue
from threading import Event, Lock, Thread, Timer

from liblistenbrainz import Listen, ListenBrainz
from liblistenbrainz.errors import ListenBrainzAPIException

from __version__ import __version__
from cache import ListenCache, describe, rejected, submit
from currentsong import Song
from logger import Logger

DEFAULT_MIN_PLAY_TIME = 30
CANONICAL_MAX_DELAY = 240
SUBMISSION_CLIENT = 'lbms'
MUSIC_SERVICES = {'Spotify': 'spotify.com'}
CLEAR = None


@dataclass
class Session:
    """started is monotonic: a Pi has no RTC and boots on fake-hwclock, so
    the wall clock can jump days forward when NTP syncs mid-track. Wall time
    is derived at submission, when the clock is most likely right."""
    song: Song
    started: float
    delay: float
    played: float = 0.0
    resumed: float | None = None
    scrobbled: bool = False
    timer: Timer | None = None


class Scrobbler:
    """Play-session state machine. A listen is due once the accumulated
    playing time (pauses excluded) reaches min(duration/2, 240s), floored
    at min_play_time; without a duration, min_play_time alone."""

    def __init__(self, settings: dict, client: ListenBrainz, cache: ListenCache | None,
                 log: Logger, dry_run: bool = False):
        self.client = client
        self.cache = cache
        self.log = log
        self.dry_run = dry_run
        features = settings['features']
        self.announce_enabled = features['enable_listening_now']
        self.listen_enabled = features['enable_listen']
        self.retry_count = max(1, int(settings['retry']['count']))
        self.retry_delay = settings['retry']['delay']
        try:
            self.min_play_time = max(0.0, float(settings.get('min_play_time', DEFAULT_MIN_PLAY_TIME)))
        except (TypeError, ValueError):
            self.min_play_time = DEFAULT_MIN_PLAY_TIME
        filters = settings.get('filters', {})
        self._fold = str if filters.get('case_sensitive', False) else str.casefold
        self._patterns = {
            field: [self._fold(p) for p in patterns if p]
            for field, patterns in filters.get('ignore_patterns', {}).items()
        }
        self._lock = Lock()
        self._session: Session | None = None
        self._stop = Event()
        self._presence: SimpleQueue[Song | None] = SimpleQueue()
        Thread(target=self._presence_worker, daemon=True).start()

    def update(self, song: Song | None) -> None:
        if song is not None:
            with self._lock:
                self._transition(song)

    def shutdown(self) -> None:
        self._stop.set()
        with self._lock:
            self._end(quiet=True)
        if self.cache is not None:
            self.cache.save()

    def run_cache(self, interval: float) -> None:
        while not self._stop.is_set():
            self.flush_cache()
            if self._stop.wait(interval):
                return

    def flush_cache(self) -> None:
        if self.cache is None or self.dry_run or not len(self.cache):
            return
        self.log.info(f"Cache: {len(self.cache)} pending")
        if self.cache.flush(self.client):
            self.log.ok("Cache done")
        else:
            self.log.warning(f"Cache partial: {len(self.cache)} left")

    def _transition(self, song: Song) -> None:
        if self._ignored(song):
            self.log.debug(f"Ignored: {song.title} - {song.artist}")
            self._end()
            return

        session = self._session
        match song.state:
            case 'play' if session and session.song.identity == song.identity:
                if session.resumed is None:
                    self.log.info(f"Resumed: {song.title}")
                    self._resume(session)
                    self._presence.put(session.song)
            case 'play':
                self._end(quiet=True)
                self._session = Session(song, time.monotonic(), self._delay(song))
                self._resume(self._session)
                self._presence.put(song)
            case 'pause':
                if session and session.resumed is not None:
                    session.played += time.monotonic() - session.resumed
                    session.resumed = None
                    self._disarm(session)
                    self.log.info(f"Paused: {session.song.title}")
                    self._presence.put(CLEAR)
            case _:
                self._end()

    def _resume(self, session: Session) -> None:
        session.resumed = time.monotonic()
        if self.listen_enabled and not session.scrobbled:
            session.timer = Timer(max(0.0, session.delay - session.played), self._due, args=(session,))
            session.timer.daemon = True
            session.timer.start()

    def _disarm(self, session: Session) -> None:
        if session.timer:
            session.timer.cancel()
            session.timer = None

    def _end(self, quiet: bool = False) -> None:
        if not (session := self._session):
            return
        self._disarm(session)
        self._session = None
        if not quiet:
            self.log.info(f"Stopped: {session.song.title}")
            self._presence.put(CLEAR)

    def _due(self, session: Session) -> None:
        with self._lock:
            if self._session is not session or session.resumed is None or session.scrobbled:
                return
            session.scrobbled = True
        self._submit_listen(session)

    def _delay(self, song: Song) -> float:
        if song.duration_ms:
            return max(min(song.duration_ms / 2000, CANONICAL_MAX_DELAY), self.min_play_time)
        return self.min_play_time

    def _ignored(self, song: Song) -> bool:
        return any(
            any(p in self._fold(getattr(song, field, '') or '') for p in patterns)
            for field, patterns in self._patterns.items()
        )

    def _payload(self, song: Song, listened_at: int | None = None) -> dict:
        info = {
            'media_player': song.source,
            'submission_client': SUBMISSION_CLIENT,
            'submission_client_version': __version__,
        }
        if service := MUSIC_SERVICES.get(song.source):
            info['music_service'] = service
        if song.tracknumber is not None:
            info['tracknumber'] = song.tracknumber
        if song.duration_ms:
            info['duration_ms'] = song.duration_ms
        payload = {
            'track_name': song.title,
            'artist_name': song.artist,
            'release_name': song.album,
            'additional_info': info,
        }
        if listened_at is not None:
            payload['listened_at'] = listened_at
        return payload

    def _presence_worker(self) -> None:
        """Listening now, in order, off the watcher thread. Only the newest
        request matters, so a backlog collapses to its last item."""
        while True:
            item = self._presence.get()
            while not self._presence.empty():
                item = self._presence.get()
            if item is CLEAR:
                self._clear()
            else:
                self._announce(item)

    def _announce(self, song: Song) -> None:
        name = f"{song.title} - {song.artist}"
        if not self.announce_enabled:
            self.log.info(f"Track: {name}")
            return
        payload = self._payload(song)
        if self.dry_run:
            self.log.info(f"[DRY] Listening now: {name}")
            self.log.debug(f"[DRY] payload: {payload}")
            return
        try:
            self.client.submit_playing_now(Listen(**payload))
            self.log.info(f"Listening now: {name}")
        except Exception as e:
            self.log.error(f"Listening now err: {describe(e)}")

    def _clear(self) -> None:
        """POST /1/playing-now/delete (2026-03). liblistenbrainz 0.7.0 has no
        wrapper; its _post carries auth, rate limit and our transport. 404
        means the status belongs to another client: nothing to clear."""
        if not self.announce_enabled or self.dry_run:
            return
        try:
            self.client._post('/1/playing-now/delete', data=json.dumps({'client': SUBMISSION_CLIENT}))
            self.log.debug("Listening now cleared")
        except Exception as e:
            if not (isinstance(e, ListenBrainzAPIException) and e.status_code == 404):
                self.log.debug(f"Listening now clear err: {describe(e)}")

    def _submit_listen(self, session: Session) -> None:
        song = session.song
        name = f"{song.title} - {song.artist}"
        payload = self._payload(song, int(time.time() - (time.monotonic() - session.started)))
        if self.dry_run:
            self.log.info(f"[DRY] Submit: {name}")
            self.log.debug(f"[DRY] payload: {payload}")
            return

        for attempt in range(1, self.retry_count + 1):
            if self._stop.is_set():
                break
            try:
                submit(self.client, [payload])
                self.log.info(f"Submitted: {name}")
                return
            except Exception as e:
                if rejected(e):
                    self.log.error(f"Rejected: {name} ({describe(e)})")
                    return
                self.log.error(f"Submit err {attempt}/{self.retry_count}: {name} ({describe(e)})")
            if attempt < self.retry_count and self._stop.wait(self.retry_delay):
                break

        if self.cache is not None:
            self.cache.add(payload)
            self.log.ok(f"Cached: {name}")
        else:
            self.log.error(f"Lost, cache disabled: {name}")
