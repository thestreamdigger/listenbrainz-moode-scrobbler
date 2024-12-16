#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ListenBrainz moOde Scrobbler
# Copyright (C) 2024 StreamDigger
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import time
import json
import os
from collections import deque
from html import unescape
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from liblistenbrainz import ListenBrainz, Listen
from threading import Thread
from logger import Logger


class ListenCache:
    def __init__(self, cache_file):
        self.cache_file = cache_file
        self.pending_listens = deque(maxlen=1000)
        self.load_cache()

    def load_cache(self):
        try:
            if not os.path.exists(self.cache_file):
                self.save_cache()
                return

            with open(self.cache_file, 'r') as f:
                content = f.read().strip()
                if content:
                    self.pending_listens = deque(json.loads(content), maxlen=1000)
                else:
                    self.save_cache()
        except json.JSONDecodeError:
            print("Cache file was corrupted. Creating new cache file.")
            self.save_cache()
        except Exception as e:
            print(f"Error handling cache file: {e}")
            self.save_cache()

    def save_cache(self):
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(list(self.pending_listens), f)
        except Exception as e:
            print(f"Failed to save cache: {e}")

    def add_listen(self, listen_dict):
        self.pending_listens.append(listen_dict)
        self.save_cache()

    def process_pending_listens(self, client):
        while self.pending_listens:
            listen_dict = self.pending_listens.popleft()
            try:
                listen = Listen(**listen_dict)
                client.submit_single_listen(listen)
                self.save_cache()
            except Exception as e:
                self.pending_listens.appendleft(listen_dict)
                self.save_cache()
                break


class ListenBrainzScrobbler(FileSystemEventHandler):
    def __init__(self):
        self.settings = self.load_settings()
        self.log = Logger(self.settings)
        self.client = ListenBrainz()
        self.token = self.settings['listenbrainz_token']
        
        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
        cache_dir = os.path.join(cache_dir, 'listenbrainz-moode-scrobbler')
        
        self.listen_cache = ListenCache(os.path.join(cache_dir, self.settings['cache_file'])) if self.settings['features']['enable_cache'] else None
        self.current_song = None
        self.play_start_time = None
        self.retry_count = self.settings['retry']['count']
        self.retry_delay = self.settings['retry']['delay']

    def validate_token(self):
        try:
            self.client.set_auth_token(self.token)
        except Exception as e:
            self.log.error(f"Token validation failed - {e}")
            exit(1)

    def parse_currentsong(self):
        self.log.debug("Starting to parse currentsong file")
        try:
            with open(self.settings['currentsong_file'], 'r', encoding='utf-8') as f:
                lines = f.readlines()
                self.log.debug(f"Read {len(lines)} lines from file")

            song_info = {
                "title": None,
                "artist": None,
                "album": None,
                "state": None
            }

            for line in lines:
                if line.startswith("title="):
                    song_info["title"] = self.clean_text(line.split("=", 1)[1])
                    self.log.debug(f"Found title: {song_info['title']}")
                elif line.startswith("artist="):
                    song_info["artist"] = self.clean_text(line.split("=", 1)[1])
                    self.log.debug(f"Found artist: {song_info['artist']}")
                elif line.startswith("album="):
                    song_info["album"] = self.clean_text(line.split("=", 1)[1])
                    self.log.debug(f"Found album: {song_info['album']}")
                elif line.startswith("state="):
                    song_info["state"] = self.clean_text(line.split("=", 1)[1])
                    self.log.debug(f"Found state: {song_info['state']}")

            if not song_info["title"] or not song_info["artist"]:
                self.log.debug("Incomplete song info detected")
                return None

            self.log.debug("Successfully parsed song info")
            return song_info

        except Exception as e:
            self.log.error(f"Error parsing song information: {str(e)}")
            return None

    def submit_playing_now(self, song_info):
        if not self.settings['features']['enable_listening_now']:
            self.log.debug("Listening now... feature disabled")
            return True

        try:
            self.log.debug("Submitting Listening now... status")
            listen = Listen(
                track_name=song_info['title'],
                artist_name=song_info['artist'],
                release_name=song_info.get('album', ''),
                listening_from='moOde audio player'
            )
            self.client.submit_playing_now(listen)
            self.log.info(f"Listening now...: {song_info['title']} by {song_info['artist']}")
            return True
        except Exception as e:
            self.log.error(f"Failed to submit Listening now...: {e}")
            return False

    def submit_listen(self, song_info):
        self.log.debug("====== Starting listen submission process ======")
        if not self.settings['features']['enable_listen']:
            self.log.debug("Listen submission is disabled in settings")
            return

        current_time = time.time()
        play_time = current_time - self.play_start_time if self.play_start_time else 0
        self.log.debug(f"Track played for {int(play_time)}s (minimum required: {self.settings['min_play_time']}s)")

        if play_time < self.settings['min_play_time']:
            self.log.info(f"Skipping submission: {song_info['title']} - Insufficient play time")
            self.log.debug("====== Listen submission process ended ======")
            return

        self.log.debug(f"Creating Listen object for: {song_info['title']}")
        listen = Listen(
            track_name=song_info['title'],
            artist_name=song_info['artist'],
            release_name=song_info.get('album', ''),
            listened_at=int(current_time),
            listening_from='moOde audio player'
        )

        for attempt in range(self.retry_count):
            try:
                self.log.debug(f"Submitting listen (attempt {attempt + 1}/{self.retry_count})")
                self.client.submit_single_listen(listen)
                self.log.info(f"Successfully submitted: {song_info['title']} by {song_info['artist']} ({song_info.get('album', 'N/A')})")
                self.log.debug("====== Listen submission process completed ======")
                return
            except Exception as e:
                self.log.error(f"Submission attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.retry_count - 1:
                    self.log.debug(f"Waiting {self.retry_delay}s before retry")
                    time.sleep(self.retry_delay)
                else:
                    self.log.error("All submission attempts failed")
                    self.log.debug("====== Listen submission process failed ======")

    def clean_text(self, text):
        if not text:
            return ""
        decoded_text = unescape(text)
        return decoded_text.strip()

    def handle_song_update(self, song_info):
        self.log.debug("Processing song update...")
        if not song_info:
            self.log.debug("No song metadata available")
            return

        if self.should_ignore(song_info):
            return

        self.log.debug(f"Current playback state: {song_info.get('state', 'unknown')}")

        if song_info.get("state") != "play":
            self.log.debug("Playback is not in play state")
            if self.current_song:
                self.log.info(f"Playback stopped: {self.current_song['title']}")
                self.log.debug("Resetting playback tracking")
                self.current_song = None
                self.play_start_time = None
            return

        if song_info != self.current_song:
            self.log.debug("New track detected")
            if self.settings['features']['enable_listening_now']:
                self.log.debug("Updating Listening now.. status")
                self.submit_playing_now(song_info)

            self.log.debug("Starting playback tracking...")
            self.play_start_time = time.time()
            self.current_song = song_info

            if self.settings['features']['enable_listen']:
                self.log.debug("Initiating scrobble delay")
                Thread(target=self._delayed_submit, args=(song_info,), daemon=True).start()

    def _delayed_submit(self, song_info):
        self.log.debug(f"Starting delayed submit for: {song_info['title']}...")
        time.sleep(self.settings['min_play_time'])
        self.log.debug(f"Delay completed, submitting listen...")
        self.submit_listen(song_info)

    def handle_initial_song(self):
        self.log.debug("Starting initial song detection")
        song_info = self.parse_currentsong()
        
        if not song_info:
            self.log.debug("No initial song information available")
            return
        
        if song_info.get("state") != "play":
            self.log.debug("Initial state is not 'play', skipping")
            return

        if self.should_ignore(song_info):
            self.log.debug("Initial song matches ignore filters, skipping")
            return

        self.log.info(f"Initial song detected: {song_info['title']} by {song_info['artist']}")

        if self.settings['features']['enable_listening_now']:
            self.log.debug("Submitting Listening now... status")
            self.submit_playing_now(song_info)
        else:
            self.log.debug("Listening now updates disabled, skipping initial status")

        self.log.debug("Setting up initial song for scrobbling")
        self.current_song = song_info
        self.play_start_time = time.time()

        if self.settings['features']['enable_listen']:
            self.log.debug("Starting scrobble delay for initial song")
            Thread(target=self._delayed_submit, args=(song_info,), daemon=True).start()
        else:
            self.log.debug("Scrobbling disabled, skipping initial listen")

    def on_modified(self, event):
        if event.src_path == self.settings['currentsong_file']:
            self.log.debug("Currentsong file changed, handling update")
            self.handle_song_update(self.parse_currentsong())

    def load_settings(self):
        try:
            with open(os.path.join(os.path.dirname(__file__), 'settings.json'), 'r') as f:
                settings = json.load(f)
                temp_logger = Logger(settings)
                temp_logger.debug("Settings loaded successfully")
                return settings
        except Exception as e:
            temp_logger = Logger({"logging": {"enable": True, "level": "ERROR"}})
            temp_logger.error(f"Error loading settings - {e}")
            exit(1)

    def should_ignore(self, song_info):
        filters = self.settings.get('filters', {})
        ignore_patterns = filters.get('ignore_patterns', {})
        case_sensitive = filters.get('case_sensitive', False)

        def match_patterns(text, patterns):
            if not text or not patterns:
                return False
            
            if not case_sensitive:
                text = text.lower()
                patterns = [p.lower() for p in patterns]
                
            return any(pattern in text for pattern in patterns)

        for field, patterns in ignore_patterns.items():
            if match_patterns(song_info.get(field, ''), patterns):
                self.log.debug(f"Ignoring content: {song_info.get('title')} (matched {field} pattern)")
                return True

        return False


def main():
    scrobbler = ListenBrainzScrobbler()
    
    scrobbler.log.info("ListenBrainz moOde Scrobbler")
    scrobbler.log.info("============================")
 
    scrobbler.log.wait("Validating ListenBrainz token...")
    scrobbler.validate_token()
    scrobbler.log.ok("Token validated successfully")

    scrobbler.handle_initial_song()

    observer = Observer()
    observer.schedule(
        scrobbler, 
        path=os.path.dirname(scrobbler.settings['currentsong_file']), 
        recursive=False
    )
    observer.start()

    try:
        scrobbler.log.info("Scrobbler is now running. Waiting for updates...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
