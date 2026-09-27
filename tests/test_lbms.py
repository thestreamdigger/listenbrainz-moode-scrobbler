import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from liblistenbrainz import ListenBrainz
from liblistenbrainz.errors import ListenBrainzAPIException
from watchdog.observers import Observer

import main
import scrobbler as scrobbler_module
from cache import ListenCache
from currentsong import Song, read
from logger import Logger
from scrobbler import Scrobbler

QUIET = Logger({'logging': {'enable': False}})


def settings(min_play_time: float = 0.2, **features) -> dict:
    return {
        'min_play_time': min_play_time,
        'features': {'enable_listening_now': True, 'enable_listen': True,
                     'enable_cache': True, **features},
        'filters': {'ignore_patterns': {'artist': ['Radio station']}, 'case_sensitive': False},
        'retry': {'count': 2, 'delay': 0},
    }


class FakeClient:
    def __init__(self, fail: list[Exception] | None = None, reject: set[str] = frozenset()):
        self.fail = list(fail or [])
        self.reject = reject
        self.single: list = []
        self.multiple: list = []
        self.presence: list[str] = []

    def _check(self, listens):
        if self.fail:
            raise self.fail.pop(0)
        if any(l.track_name in self.reject for l in listens):
            raise ListenBrainzAPIException(400, 'rejected')

    def submit_single_listen(self, listen):
        self._check([listen])
        self.single.append(listen)

    def submit_multiple_listens(self, listens):
        self._check(listens)
        self.multiple.append(listens)

    def submit_playing_now(self, listen):
        self.presence.append(listen.track_name)

    def _post(self, endpoint, data=None):
        self.presence.append(endpoint)


def song(title: str = 'T', state: str = 'play', duration_ms: int | None = None, **kw) -> Song:
    return Song(title=title, artist=kw.pop('artist', 'A'), album=kw.pop('album', 'B'),
                state=state, duration_ms=duration_ms, **kw)


def listen(n: int) -> dict:
    return {'track_name': f't{n}', 'artist_name': 'a', 'listened_at': 1_700_000_000 + n}


def wait_for(predicate, timeout: float = 2.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


class CurrentSongTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / 'currentsong.txt'

    def tearDown(self):
        self.dir.cleanup()

    def parse(self, text: str) -> Song | None:
        self.path.write_text(text, encoding='utf-8')
        return read(self.path)

    def test_mpd_track(self):
        s = self.parse("file=NAS/x.flac\nartist=Nina &amp; Co\nalbum=Alb\ntitle=Tune\n"
                       "track=3/12\nduration=241\nstate=play\nelapsed=12\n")
        self.assertEqual((s.title, s.artist, s.album, s.state), ('Tune', 'Nina & Co', 'Alb', 'play'))
        self.assertEqual((s.tracknumber, s.duration_ms, s.source), (3, 241000, 'MPD'))

    def test_radio_has_no_duration(self):
        s = self.parse("file=http://x/stream\nartist=Radio station\nalbum=FM\ntitle=A - B\n"
                       "duration=0\nstate=play\n")
        self.assertIsNone(s.duration_ms)

    def test_stopped_mpd(self):
        s = self.parse("file=NAS/x.flac\nartist=A\ntitle=T\nstate=stop\nelapsed=\nduration=\n")
        self.assertEqual((s.state, s.duration_ms), ('stop', None))

    def test_renderer_playing_takes_duration_from_moode_cache(self):
        (self.path.parent / 'spotmeta.json').write_text(json.dumps(
            {'title': 'T', 'artist': 'A', 'album': 'B', 'duration': '200000'}))
        s = self.parse("file=Spotify Active\nartist=A\nalbum=B\ntitle=T\noutrate=PCM 16/44.1 kHz, 2ch\n")
        self.assertEqual((s.state, s.source, s.duration_ms), ('play', 'Spotify', 200000))

    def test_renderer_cache_for_other_track_is_ignored(self):
        (self.path.parent / 'aplmeta.json').write_text(json.dumps(
            {'title': 'Previous', 'artist': 'A', 'duration': '200000'}))
        s = self.parse("file=AirPlay Active\nartist=A\nalbum=B\ntitle=T\n")
        self.assertEqual((s.source, s.duration_ms), ('AirPlay', None))

    def test_renderer_without_metadata_is_paused(self):
        s = self.parse("file=AirPlay Active\noutrate=Not playing\n")
        self.assertEqual((s.state, s.source), ('pause', 'AirPlay'))

    def test_other_renderers_stop(self):
        for marker, source in (('Qobuz Active', 'Qobuz'), ('Bluetooth Active', 'Bluetooth'),
                               ('Analog Input Active', 'Analog Input')):
            s = self.parse(f"file={marker}\noutrate=Not playing\n")
            self.assertEqual((s.state, s.source), ('stop', source))

    def test_incomplete_file_is_none(self):
        self.assertIsNone(self.parse(""))
        self.assertIsNone(self.parse("file=NAS/x.flac\nartist=A\ntitle=T\n"))
        self.assertIsNone(self.parse("file=NAS/x.flac\nstate=play\n"))

    def test_bad_numbers_are_dropped(self):
        s = self.parse("file=x\nartist=A\ntitle=T\ntrack=x\nduration=\nstate=play\n")
        self.assertEqual((s.tracknumber, s.duration_ms), (None, None))


class CacheTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / 'cache' / 'pending.json'

    def tearDown(self):
        self.dir.cleanup()

    def test_persists_across_instances(self):
        ListenCache(self.path, QUIET).add(listen(1))
        self.assertEqual(len(ListenCache(self.path, QUIET)), 1)

    def test_flush_drains_in_batches(self):
        cache = ListenCache(self.path, QUIET)
        for n in range(120):
            cache.add(listen(n))
        client = FakeClient()
        self.assertTrue(cache.flush(client))
        self.assertEqual([len(b) for b in client.multiple], [50, 50, 20])
        self.assertEqual(json.loads(self.path.read_text()), [])

    def test_transient_failure_keeps_order(self):
        cache = ListenCache(self.path, QUIET)
        for n in range(3):
            cache.add(listen(n))
        self.assertFalse(cache.flush(FakeClient(fail=[ConnectionError()])))
        client = FakeClient()
        cache.flush(client)
        self.assertEqual([l.track_name for l in client.multiple[0]], ['t0', 't1', 't2'])

    def test_rejected_listen_is_isolated_and_dropped(self):
        cache = ListenCache(self.path, QUIET)
        for n in range(3):
            cache.add(listen(n))
        client = FakeClient(reject={'t1'})
        self.assertTrue(cache.flush(client))
        self.assertEqual(client.multiple, [])
        self.assertEqual([l.track_name for l in client.single], ['t0', 't2'])
        self.assertEqual(len(cache), 0)

    def test_legacy_cache_entries_still_submit(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(json.dumps([{
            'track_name': 't', 'artist_name': 'a', 'release_name': None, 'listened_at': 1_700_000_000,
            'additional_info': {'tracknumber': 3, 'release_mbid': 'x', 'submission_client': 'lbms'}}]))
        client = FakeClient()
        self.assertTrue(ListenCache(self.path, QUIET).flush(client))
        self.assertEqual(len(client.single), 1)

    def test_corrupt_file_is_backed_up(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('{not json')
        cache = ListenCache(self.path, QUIET)
        self.assertEqual(len(cache), 0)
        self.assertEqual(len(list(self.path.parent.glob('pending.json.corrupt.*'))), 1)


class SessionTest(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.scrobbler = Scrobbler(settings(), self.client, None, QUIET)

    def tearDown(self):
        self.scrobbler.shutdown()

    def settle(self, seconds: float = 0.35):
        time.sleep(seconds)

    def test_play_scrobbles_once_after_delay(self):
        self.scrobbler.update(song())
        self.scrobbler.update(song())
        self.settle()
        self.assertEqual(len(self.client.single), 1)
        self.assertEqual(self.client.presence, ['T'])

    def test_pause_accumulates_played_time(self):
        self.scrobbler.update(song())
        time.sleep(0.12)
        self.scrobbler.update(song(state='pause'))
        time.sleep(0.3)
        self.assertEqual(self.client.single, [])
        start = time.monotonic()
        self.scrobbler.update(song())
        self.assertTrue(wait_for(lambda: self.client.single, 1))
        self.assertLess(time.monotonic() - start, 0.18)

    def test_pause_clears_listening_now_and_resume_restores_it(self):
        self.scrobbler.update(song())
        self.assertTrue(wait_for(lambda: self.client.presence == ['T']))
        self.scrobbler.update(song(state='pause'))
        self.assertTrue(wait_for(lambda: len(self.client.presence) == 2))
        self.scrobbler.update(song())
        self.assertTrue(wait_for(lambda: len(self.client.presence) == 3))
        self.assertEqual(self.client.presence, ['T', '/1/playing-now/delete', 'T'])

    def test_listened_at_is_first_start(self):
        t0 = int(time.time())
        self.scrobbler.update(song())
        self.scrobbler.update(song(state='pause'))
        self.scrobbler.update(song())
        self.settle()
        self.assertIn(self.client.single[0].listened_at, (t0, t0 + 1))

    def test_listened_at_survives_clock_jump(self):
        jump = 6 * 86400

        class Clock:
            offset = 0
            monotonic = staticmethod(time.monotonic)

            @classmethod
            def time(cls):
                return time.time() + cls.offset

        original, scrobbler_module.time = scrobbler_module.time, Clock
        try:
            self.scrobbler.update(song())
            Clock.offset = jump
            self.settle()
        finally:
            scrobbler_module.time = original
        start_in_synced_clock = time.time() + jump - 0.35
        self.assertAlmostEqual(self.client.single[0].listened_at, start_in_synced_clock, delta=2)

    def test_skip_before_delay_does_not_scrobble(self):
        self.scrobbler.update(song('one'))
        time.sleep(0.05)
        self.scrobbler.update(song('two'))
        self.settle()
        self.assertEqual([l.track_name for l in self.client.single], ['two'])

    def test_stop_cancels(self):
        self.scrobbler.update(song())
        self.scrobbler.update(song(state='stop'))
        self.settle()
        self.assertEqual(self.client.single, [])

    def test_renderer_takeover_ends_mpd_session(self):
        self.scrobbler.update(song())
        self.scrobbler.update(Song(title='', artist='', state='stop', source='Qobuz'))
        self.settle()
        self.assertEqual(self.client.single, [])

    def test_ignored_track_ends_session(self):
        self.scrobbler.update(song('one'))
        self.scrobbler.update(song('Station', artist='Radio station'))
        self.settle()
        self.assertEqual(self.client.single, [])
        self.scrobbler.update(song('one'))
        self.settle()
        self.assertEqual(len(self.client.single), 1)

    def test_canonical_delay(self):
        s = Scrobbler(settings(min_play_time=30), self.client, None, QUIET)
        self.assertEqual(s._delay(song(duration_ms=100_000)), 50)
        self.assertEqual(s._delay(song(duration_ms=900_000)), 240)
        self.assertEqual(s._delay(song(duration_ms=20_000)), 30)
        self.assertEqual(s._delay(song()), 30)

    def test_failure_goes_to_cache(self):
        with tempfile.TemporaryDirectory() as d:
            cache = ListenCache(Path(d) / 'c.json', QUIET)
            client = FakeClient(fail=[ConnectionError(), ConnectionError()])
            s = Scrobbler(settings(), client, cache, QUIET)
            s.update(song())
            self.assertTrue(wait_for(lambda: len(cache) == 1))
            s.shutdown()

    def test_rejected_is_not_cached(self):
        with tempfile.TemporaryDirectory() as d:
            cache = ListenCache(Path(d) / 'c.json', QUIET)
            s = Scrobbler(settings(), FakeClient(reject={'T'}), cache, QUIET)
            s.update(song())
            self.settle()
            self.assertEqual(len(cache), 0)
            s.shutdown()


class FakeListenBrainz(BaseHTTPRequestHandler):
    requests: list[tuple[str, str]] = []
    delay = 0.0
    valid = True

    def log_message(self, *args):
        pass

    def _reply(self, body: dict):
        time.sleep(self.delay)
        FakeListenBrainz.requests.append((self.path, self.headers.get('User-Agent', '')))
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._reply({'valid': FakeListenBrainz.valid, 'user_name': 'x'})

    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        self._reply({'status': 'ok'})


class TransportTest(unittest.TestCase):
    def setUp(self):
        FakeListenBrainz.requests = []
        FakeListenBrainz.delay = 0.0
        FakeListenBrainz.valid = True
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), FakeListenBrainz)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def connect(self, url: str) -> ListenBrainz:
        original = main.ListenBrainz
        main.ListenBrainz = lambda: ListenBrainz(api_base_url=url)
        try:
            return main.connect('t')
        finally:
            main.ListenBrainz = original

    def validate(self, url: str) -> tuple[bool, str, float]:
        client, out, invalid = self.connect(url), io.StringIO(), threading.Event()
        start = time.monotonic()
        with contextlib.redirect_stdout(out):
            main.validate(client, 't', Logger(), invalid)
        return invalid.is_set(), out.getvalue(), time.monotonic() - start

    def test_user_agent_on_every_call(self):
        client = self.connect(self.url)
        main.validate(client, 't', QUIET, threading.Event())
        s = Scrobbler(settings(), client, None, QUIET)
        s.update(song())
        self.assertTrue(wait_for(lambda: len(FakeListenBrainz.requests) >= 3))
        s.shutdown()
        paths = [p for p, _ in FakeListenBrainz.requests]
        self.assertEqual(paths, ['/1/validate-token', '/1/submit-listens', '/1/submit-listens'])
        self.assertTrue(all(ua.startswith('lbms/') for _, ua in FakeListenBrainz.requests))

    def test_invalid_token_is_fatal(self):
        FakeListenBrainz.valid = False
        invalid, out, _ = self.validate(self.url)
        self.assertTrue(invalid)
        self.assertIn("Token invalid", out)

    def test_stalled_server_times_out(self):
        original = main.HTTP_TIMEOUT
        main.HTTP_TIMEOUT = (0.2, 0.2)
        FakeListenBrainz.delay = 5.0
        try:
            invalid, out, elapsed = self.validate(self.url)
        finally:
            main.HTTP_TIMEOUT = original
        self.assertFalse(invalid)
        self.assertIn("Token unchecked, offline", out)
        self.assertLess(elapsed, 4.0)

    def test_offline_is_not_fatal(self):
        closed = ThreadingHTTPServer(('127.0.0.1', 0), FakeListenBrainz)
        port = closed.server_address[1]
        closed.server_close()
        invalid, out, _ = self.validate(f"http://127.0.0.1:{port}")
        self.assertFalse(invalid)
        self.assertIn("Token unchecked, offline", out)


class WatcherTest(unittest.TestCase):
    """Both ways moOde publishes currentsong.txt reach the scrobbler whole."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.www = Path(self.dir.name) / 'www'
        self.tmp = Path(self.dir.name) / 'tmp'
        self.www.mkdir()
        self.tmp.mkdir()
        self.path = self.www / 'currentsong.txt'
        self.seen: list[Song | None] = []
        recorder = type('Recorder', (), {'update': lambda _, s: self.seen.append(s)})()
        self.handler = main.CurrentSongHandler(self.path, recorder, QUIET)
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.www), recursive=False,
                               event_filter=self.handler.EVENTS)
        self.observer.start()

    def tearDown(self):
        self.observer.stop()
        self.observer.join()
        self.dir.cleanup()

    def content(self, title: str) -> str:
        return f"file=NAS/x.flac\nartist=A\nalbum=B\ntitle={title}\nstate=play\nduration=100\n"

    def test_in_place_rewrite(self):
        self.path.write_text(self.content('first'))
        with open(self.path, 'w') as f:
            f.write(self.content('second'))
        (self.www / 'aplmeta.json').write_text('{}')
        self.assertTrue(wait_for(lambda: any(s and s.title == 'second' for s in self.seen)))
        time.sleep(0.2)
        self.assertTrue(all(s is None or s.title in ('first', 'second') for s in self.seen))
        self.assertLessEqual(len(self.seen), 3)

    def test_rename_from_other_directory(self):
        staged = self.tmp / 'currentsong.txt'
        staged.write_text(self.content('renamed'))
        os.replace(staged, self.path)
        self.assertTrue(wait_for(lambda: any(s and s.title == 'renamed' for s in self.seen)))


if __name__ == '__main__':
    unittest.main()
