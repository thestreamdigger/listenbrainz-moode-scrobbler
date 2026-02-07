#!/usr/bin/env python3
#
# ListenBrainz moOde Scrobbler v1.1.0
# Copyright (C) 2025 StreamDigger
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Standard library
import json
import os
import signal
import sys
import tempfile
import time
from collections import deque
from html import unescape
from threading import Lock, Thread, Timer

# Third-party
from dotenv import load_dotenv
from liblistenbrainz import Listen, ListenBrainz
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Local
from __version__ import __copyright__, __version__
from logger import Logger

# Constants
MAX_CACHE_SIZE = 1000
SMALL_QUEUE_THRESHOLD = 3
BATCH_SIZE = 10
CONNECTION_CHECK_INTERVAL = 60
SAVE_DELAY = 5
DEFAULT_MIN_PLAY_TIME = 30
LISTENING_FROM = 'moOde audio player'

SONG_FIELDS = {
    'title', 'artist', 'album', 'state', 'track', 'date',
    'composer', 'genre', 'duration', 'bitrate', 'encoded'
}
SONG_IDENTITY_FIELDS = ('title', 'artist', 'album')


def print_banner():
    print(f"\nLISTENBRAINZ-MOODE-SCROBBLER\nVersion {__version__}\n{__copyright__}\n")


class ListenCache:
    """Manages cached listen submissions with atomic file operations and thread-safe locking."""

    def __init__(self, cache_file, logger):
        self.cache_file = cache_file
        self.pending_listens = deque(maxlen=MAX_CACHE_SIZE)
        self.log = logger
        self._save_timer = None
        self._lock = Lock()
        self.load_cache()

    def load_cache(self):
        with self._lock:
            try:
                if not os.path.exists(self.cache_file):
                    self._save_unlocked()
                    return

                with open(self.cache_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        self.pending_listens = deque(json.loads(content), maxlen=MAX_CACHE_SIZE)
                    else:
                        self._save_unlocked()
            except Exception as e:
                self.log.error(f"Error handling cache file: {e}")
                self._save_unlocked()

    def _save_unlocked(self):
        """Atomic write (temp file + replace). Caller must hold self._lock."""
        try:
            if self._save_timer:
                self._save_timer.cancel()
                self._save_timer = None

            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)

            temp_fd, temp_path = tempfile.mkstemp(
                prefix=".lbms_cache_", dir=cache_dir if cache_dir else None
            )
            try:
                with os.fdopen(temp_fd, 'w') as tmp_f:
                    json.dump(list(self.pending_listens), tmp_f)
                os.replace(temp_path, self.cache_file)
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
        except Exception as e:
            self.log.error(f"Failed to save cache: {e}")

    def save_cache(self):
        with self._lock:
            self._save_unlocked()

    def _schedule_save(self):
        with self._lock:
            if self._save_timer:
                self._save_timer.cancel()

            self._save_timer = Timer(SAVE_DELAY, self.save_cache)
            self._save_timer.start()

    def add_listen(self, listen_dict):
        with self._lock:
            self.pending_listens.append(listen_dict)
        self._schedule_save()

    def has_pending(self):
        with self._lock:
            return len(self.pending_listens) > 0

    def process_pending_listens(self, client):
        """Uses single submission for small queues, batch for larger ones."""
        with self._lock:
            small_queue = len(self.pending_listens) < SMALL_QUEUE_THRESHOLD

        if small_queue:
            to_process = []
            with self._lock:
                while self.pending_listens:
                    to_process.append(self.pending_listens.popleft())

            for listen_dict in to_process:
                try:
                    listen = Listen(**listen_dict)
                    client.submit_single_listen(listen)
                    self._schedule_save()
                except Exception:
                    with self._lock:
                        self.pending_listens.appendleft(listen_dict)
                    self._schedule_save()
                    return False
            return True

        with self._lock:
            batch_size = min(BATCH_SIZE, len(self.pending_listens))
            extracted = []
            for _ in range(batch_size):
                if not self.pending_listens:
                    break
                extracted.append(self.pending_listens.popleft())

        batch = []
        valid_dicts = []
        for listen_dict in extracted:
            try:
                batch.append(Listen(**listen_dict))
                valid_dicts.append(listen_dict)
            except Exception as e:
                self.log.error(f"Dropping invalid listen: {e}")

        if batch:
            try:
                client.submit_multiple_listens(batch)
                self._schedule_save()
                return True
            except Exception:
                with self._lock:
                    for listen_dict in reversed(valid_dicts):
                        self.pending_listens.appendleft(listen_dict)
                self._schedule_save()
                return False

        return True


class ListenBrainzScrobbler(FileSystemEventHandler):
    """Monitors moOde currentsong.txt and submits listens to ListenBrainz with caching support."""

    def __init__(self):
        print_banner()

        load_dotenv()

        self.settings = self._load_settings()
        self.log = Logger(self.settings)
        self.log.debug("Settings loaded successfully")
        self.client = None

        self._token = os.getenv('LISTENBRAINZ_TOKEN') or self.settings.get('listenbrainz_token')

        if not self._token:
            self.log.error("LISTENBRAINZ_TOKEN not found in environment or settings.json")
            raise ValueError("LISTENBRAINZ_TOKEN not found in environment or settings.json")

        self.current_song = None
        self.play_start_time = None
        self.retry_count = self.settings['retry']['count']
        self.retry_delay = self.settings['retry']['delay']

        try:
            self.min_play_time = max(0, int(self.settings.get('min_play_time', DEFAULT_MIN_PLAY_TIME)))
        except Exception:
            self.min_play_time = DEFAULT_MIN_PLAY_TIME

        self._currentsong_realpath = os.path.realpath(self.settings['currentsong_file'])
        self.listen_cache = None
        self._preprocess_filters()

    def _preprocess_filters(self):
        filters = self.settings.get('filters', {})
        self._case_sensitive = filters.get('case_sensitive', False)

        self._ignore_patterns = {}
        for field, patterns in filters.get('ignore_patterns', {}).items():
            if self._case_sensitive:
                self._ignore_patterns[field] = patterns
            else:
                self._ignore_patterns[field] = [p.lower() for p in patterns]

    def _safe_log_error(self, message):
        safe_msg = message.replace(self._token, "****")
        self.log.error(safe_msg)

    def initialize(self):
        self.log.wait("Validating ListenBrainz token...")
        try:
            self.client = ListenBrainz()
            self.client.set_auth_token(self._token)
            self.log.ok("Token validated successfully")
        except Exception as e:
            self._safe_log_error(f"Token validation failed - {e}")
            return False

        if self.settings['features']['enable_cache']:
            cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
            self.listen_cache = ListenCache(
                os.path.join(cache_dir, self.settings['cache_file']),
                self.log
            )
            Thread(target=self._check_connection_periodically, daemon=True).start()

        return True

    def _check_connection_periodically(self):
        while True:
            time.sleep(CONNECTION_CHECK_INTERVAL)
            self.check_connection_and_process_cache()

    def check_connection_and_process_cache(self):
        if not self.listen_cache or not self.listen_cache.has_pending():
            return

        try:
            self.log.info("Processing pending listens...")

            if self.listen_cache.process_pending_listens(self.client):
                self.log.ok("Cache processed successfully")
            else:
                self.log.warning("Partial cache processing")

        except Exception as e:
            self.log.debug(f"Connection check failed: {e}")

    def check_initial_playback(self):
        self.log.info("Checking for currently playing track...")
        initial_song = self.parse_currentsong()

        if initial_song and initial_song.get("state") == "play":
            self.log.info(f"Found playing track: {initial_song.get('title')} by {initial_song.get('artist')}")
            self.handle_song_update(initial_song)
        else:
            self.log.info("No track currently playing")

    def parse_currentsong(self):
        try:
            with open(self.settings['currentsong_file'], 'r', encoding='utf-8') as f:
                lines = f.readlines()

            song_info = {field: None for field in SONG_FIELDS}

            for line in lines:
                key, sep, value = line.partition("=")
                if sep and key in SONG_FIELDS:
                    song_info[key] = self._clean_text(value)

            if song_info['state']:
                song_info['state'] = song_info['state'].lower()

            if not song_info['title'] or not song_info['artist']:
                self.log.debug("Invalid song info: missing title or artist")
                return None

            return song_info

        except Exception as e:
            self.log.error(f"Error parsing song information: {str(e)}")
            return None

    def _extract_tracknumber(self, song_info):
        if not song_info.get('track'):
            return None
        try:
            return int(song_info['track'].split('/')[0])
        except (ValueError, AttributeError):
            return None

    def _same_track(self, a, b):
        if a is None or b is None:
            return False
        return all(a.get(f) == b.get(f) for f in SONG_IDENTITY_FIELDS)

    def submit_playing_now(self, song_info):
        try:
            tracknumber = self._extract_tracknumber(song_info)

            listen = Listen(
                track_name=song_info['title'],
                artist_name=song_info['artist'],
                release_name=song_info.get('album', ''),
                listening_from=LISTENING_FROM,
                tracknumber=tracknumber
            )
            self.client.submit_playing_now(listen)
            self.log.info(f"Listening now... {song_info['title']} by {song_info['artist']}")
            return True
        except Exception as e:
            self._safe_log_error(f"Failed to submit Listening now...: {e}")
            return False

    def submit_listen(self, song_info, play_start_time):
        if not self.settings['features']['enable_listen']:
            return

        play_time = time.time() - play_start_time

        if play_time < self.min_play_time:
            self.log.debug(f"Skipping submission: {song_info.get('title')} - Insufficient play time")
            return

        tracknumber = self._extract_tracknumber(song_info)

        listen = Listen(
            track_name=song_info['title'],
            artist_name=song_info['artist'],
            release_name=song_info.get('album', ''),
            listened_at=int(time.time()),
            listening_from=LISTENING_FROM,
            tracknumber=tracknumber
        )

        for attempt in range(self.retry_count):
            try:
                self.client.submit_single_listen(listen)
                self.log.info(f"Successfully submitted: {song_info['title']} by {song_info['artist']}")
                return
            except Exception as e:
                self.log.error(f"Submission failed for '{song_info['title']}' by '{song_info['artist']}'")
                self._safe_log_error(f"Attempt {attempt + 1}/{self.retry_count} - Error: {e}")
                if attempt < self.retry_count - 1:
                    self.log.wait(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    self.log.error("All retry attempts exhausted")

        if self.listen_cache:
            self.log.wait("Saving failed submission to cache for later retry...")
            self.listen_cache.add_listen({
                'track_name': song_info.get('title', ''),
                'artist_name': song_info.get('artist', ''),
                'release_name': song_info.get('album', ''),
                'listened_at': int(time.time()),
                'listening_from': LISTENING_FROM,
                'tracknumber': tracknumber
            })
            self.log.ok("Submission saved to cache")
        else:
            self.log.error("Submission lost - Cache feature is disabled")

    def _clean_text(self, text):
        if not text:
            return ""
        return unescape(text).strip()

    def handle_song_update(self, song_info):
        if not song_info:
            return

        if self._should_ignore(song_info):
            return

        self.log.debug(f"Processing state: {song_info.get('state', 'unknown')}")

        if song_info.get("state") != "play":
            if self.current_song:
                self.log.info(f"Playback stopped: {self.current_song.get('title')}")
                self.current_song = None
                self.play_start_time = None
            return

        if not self._same_track(song_info, self.current_song):
            if self.settings['features']['enable_listening_now']:
                self.submit_playing_now(song_info)
            else:
                self.log.info(f"Track detected: {song_info.get('title')} by {song_info.get('artist')}")

            self.current_song = song_info
            self.play_start_time = time.time()

            if self.settings['features']['enable_listen']:
                play_start = self.play_start_time
                Thread(target=self._delayed_submit, args=(song_info, play_start), daemon=True).start()

    def _delayed_submit(self, song_info, play_start_time):
        self.log.debug(f"Delayed submit started for: {song_info.get('title')}")
        time.sleep(self.min_play_time)
        self.submit_listen(song_info, play_start_time)

    def _handle_file_change(self, event_type):
        try:
            self.log.debug(f"Currentsong file {event_type}, handling update")
            self.handle_song_update(self.parse_currentsong())
        except Exception as e:
            self.log.debug(f"Error handling file {event_type}: {e}")

    def on_modified(self, event):
        if os.path.realpath(event.src_path) == self._currentsong_realpath:
            self._handle_file_change("changed")

    def on_created(self, event):
        if os.path.realpath(event.src_path) == self._currentsong_realpath:
            self._handle_file_change("created")

    def _load_settings(self):
        settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Settings file not found: {settings_path}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in settings file: {e.msg}", e.doc, e.pos)

    def _should_ignore(self, song_info):
        def match_patterns(text, patterns):
            if not text or not patterns:
                return False

            if not self._case_sensitive:
                text = text.lower()

            return any(pattern in text for pattern in patterns)

        for field, patterns in self._ignore_patterns.items():
            if match_patterns(song_info.get(field, ''), patterns):
                self.log.debug(f"Ignoring content: {song_info.get('title')} (matched {field} pattern)")
                return True

        return False

    def cleanup(self):
        if self.listen_cache:
            self.listen_cache.save_cache()


def main():
    scrobbler = None
    observer = None

    def signal_handler(signum, frame):
        if scrobbler:
            scrobbler.log.info(f"Received signal {signum}, shutting down gracefully...")
            scrobbler.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        scrobbler = ListenBrainzScrobbler()

        if not scrobbler.initialize():
            scrobbler.log.error("Initialization failed. Exiting...")
            return 1

        observer = Observer()
        observer.schedule(
            scrobbler,
            path=os.path.dirname(scrobbler.settings['currentsong_file']),
            recursive=False
        )

        observer.start()
        scrobbler.log.info("File monitoring started")

        scrobbler.check_initial_playback()

        scrobbler.log.info("Scrobbler is now running. Waiting for updates...")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        if scrobbler:
            scrobbler.log.info("Received shutdown signal...")
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Configuration error: {e}")
        return 1
    except Exception as e:
        if scrobbler:
            scrobbler.log.error(f"Fatal error: {e}")
        else:
            print(f"Fatal error: {e}")
        return 1
    finally:
        if observer:
            observer.stop()
            observer.join()
        if scrobbler:
            scrobbler.log.info("Shutting down...")
            scrobbler.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
