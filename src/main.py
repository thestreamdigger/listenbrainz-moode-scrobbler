#!/usr/bin/env python3
#
# ListenBrainz moOde Scrobbler v0.1.0
# Copyright (C) 2025 StreamDigger
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import time
import json
import os
from collections import deque
from html import unescape
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from liblistenbrainz import ListenBrainz, Listen
from threading import Thread, Lock
import sys
from logger import Logger
from __version__ import __version__, __author__, __copyright__


def print_banner():
    banner = f"""
LISTENBRAINZ-MOODE-SCROBBLER
Version {__version__}
{__copyright__}
"""
    return banner


class ListenCache:
    def __init__(self, cache_file, logger):
        self.cache_file = cache_file
        self.pending_listens = deque(maxlen=1000)
        self.log = logger
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
        except Exception as e:
            self.log.error(f"Error handling cache file: {e}")
            self.save_cache()

    def save_cache(self):
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(list(self.pending_listens), f)
        except Exception as e:
            self.log.error(f"Failed to save cache: {e}")

    def add_listen(self, listen_dict):
        self.pending_listens.append(listen_dict)
        self.save_cache()

    def process_pending_listens(self, client):
        if len(self.pending_listens) < 3:
            while self.pending_listens:
                listen_dict = self.pending_listens.popleft()
                try:
                    listen = Listen(**listen_dict)
                    client.submit_single_listen(listen)
                    self.save_cache()
                except Exception:
                    self.pending_listens.appendleft(listen_dict)
                    self.save_cache()
                    return False
            return True
        
        batch_size = min(10, len(self.pending_listens))
        batch = []
        
        for _ in range(batch_size):
            if not self.pending_listens:
                break
            listen_dict = self.pending_listens.popleft()
            try:
                listen = Listen(**listen_dict)
                batch.append(listen)
            except Exception as e:
                self.log.error(f"Error creating Listen object: {e}")
                self.pending_listens.appendleft(listen_dict)
        
        if batch:
            try:
                client.submit_listens(batch)
                self.save_cache()
                return True
            except Exception:
                for listen in batch:
                    self.pending_listens.appendleft({
                        'track_name': listen.track_name,
                        'artist_name': listen.artist_name,
                        'release_name': listen.release_name,
                        'listened_at': listen.listened_at,
                        'listening_from': listen.listening_from
                    })
                self.save_cache()
                return False
        
        return True


class ListenBrainzScrobbler(FileSystemEventHandler):
    def __init__(self):
        print(print_banner())
        self.settings = self.load_settings()
        self.log = Logger(self.settings)
        self.log.debug("Settings loaded successfully")
        self.client = None
        self.token = self.settings['listenbrainz_token']
        
        self.current_song = None
        self.play_start_time = None
        self.retry_count = self.settings['retry']['count']
        self.retry_delay = self.settings['retry']['delay']
        
        self.listen_cache = None

    def initialize(self):
        self.log.wait("Validating ListenBrainz token...")
        try:
            self.client = ListenBrainz()
            self.client.set_auth_token(self.token)
            self.log.ok("Token validated successfully")
        except Exception as e:
            self.log.error(f"Token validation failed - {e}")
            return False

        if self.settings['features']['enable_cache']:
            cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
            cache_dir = os.path.join(cache_dir, 'listenbrainz-moode-scrobbler')
            self.listen_cache = ListenCache(
                os.path.join(cache_dir, self.settings['cache_file']),
                self.log
            )
            Thread(target=self._check_connection_periodically, daemon=True).start()

        return True

    def _check_connection_periodically(self):
        while True:
            time.sleep(60)
            self.check_connection_and_process_cache()
            
    def check_connection_and_process_cache(self):
        if not self.settings['features']['enable_cache'] or not self.listen_cache:
            return
            
        if not self.listen_cache.pending_listens:
            return
            
        try:
            self.client.validate_listen_payload({})
            
            pending_count = len(self.listen_cache.pending_listens)
            if pending_count > 0:
                self.log.info(f"Connection restored. Processing {pending_count} pending listens...")
                
                success = self.listen_cache.process_pending_listens(self.client)
                
                if success:
                    self.log.ok(f"Cache processed successfully after reconnection")
                else:
                    self.log.warning("Partial cache processing after reconnection")
                    
        except Exception:
            pass

    def check_initial_playback(self):
        self.log.info("Checking for currently playing track...")
        initial_song = self.parse_currentsong()
        
        if initial_song and initial_song.get("state") == "play":
            self.log.info(f"Found playing track: {initial_song['title']} by {initial_song['artist']}")
            self.handle_song_update(initial_song)
        else:
            self.log.info("No track currently playing")

    def parse_currentsong(self):
        try:
            with open(self.settings['currentsong_file'], 'r', encoding='utf-8') as f:
                lines = f.readlines()

            song_info = {
                "title": None,
                "artist": None,
                "album": None,
                "state": None
            }

            for line in lines:
                if line.startswith("title="):
                    song_info["title"] = self.clean_text(line.split("=", 1)[1])
                elif line.startswith("artist="):
                    song_info["artist"] = self.clean_text(line.split("=", 1)[1])
                elif line.startswith("album="):
                    song_info["album"] = self.clean_text(line.split("=", 1)[1])
                elif line.startswith("state="):
                    song_info["state"] = self.clean_text(line.split("=", 1)[1])

            if not song_info["title"] or not song_info["artist"]:
                self.log.debug("Invalid song info: missing title or artist")
                return None

            return song_info

        except Exception as e:
            self.log.error(f"Error parsing song information: {str(e)}")
            return None

    def submit_playing_now(self, song_info):
        """Print a message without any prefix"""
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
            self.log.info(f"Listening now... {song_info['title']} by {song_info['artist']}")
            return True
        except Exception as e:
            self.log.error(f"Failed to submit Listening now...: {e}")
            return False

    def submit_listen(self, song_info):
        if not self.settings['features']['enable_listen']:
            return

        current_time = time.time()
        play_time = current_time - self.play_start_time if self.play_start_time else 0

        if play_time < self.settings['min_play_time']:
            self.log.debug(f"Skipping submission: {song_info['title']} - Insufficient play time")
            return

        listen = Listen(
            track_name=song_info['title'],
            artist_name=song_info['artist'],
            release_name=song_info.get('album', ''),
            listened_at=int(current_time),
            listening_from='moOde audio player'
        )

        for attempt in range(self.retry_count):
            try:
                self.client.submit_single_listen(listen)
                self.log.info(f"Successfully submitted: {song_info['title']} by {song_info['artist']}")
                return
            except Exception as e:
                self.log.error(f"Submission failed for '{song_info['title']}' by '{song_info['artist']}'")
                self.log.error(f"Attempt {attempt + 1}/{self.retry_count} - Error: {str(e)}")
                if attempt < self.retry_count - 1:
                    self.log.wait(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    self.log.error("All retry attempts exhausted")

        if self.settings['features']['enable_cache']:
            self.log.wait("Saving failed submission to cache for later retry...")
            self.listen_cache.add_listen({
                'track_name': song_info['title'],
                'artist_name': song_info['artist'],
                'release_name': song_info.get('album', ''),
                'listened_at': int(time.time()),
                'listening_from': 'moOde audio player'
            })
            self.log.ok("Submission saved to cache")
        else:
            self.log.error("Submission lost - Cache feature is disabled")

    def clean_text(self, text):
        if not text:
            return ""
        decoded_text = unescape(text)
        return decoded_text.strip()

    def handle_song_update(self, song_info):
        if not song_info:
            return

        if self.should_ignore(song_info):
            return

        self.log.debug(f"Processing state: {song_info.get('state', 'unknown')}")

        if song_info.get("state") != "play":
            if self.current_song:
                self.log.info(f"Playback stopped: {self.current_song['title']}")
                self.current_song = None
                self.play_start_time = None
            return

        if song_info != self.current_song:
            if self.settings['features']['enable_listening_now']:
                self.submit_playing_now(song_info)
            else:
                self.log.info(f"Track detected: {song_info['title']} by {song_info['artist']}")
            
            self.current_song = song_info
            self.play_start_time = time.time()

            if self.settings['features']['enable_listen']:
                self.log.debug("Starting scrobble delay")
                Thread(target=self._delayed_submit, args=(song_info,), daemon=True).start()

    def _delayed_submit(self, song_info):
        self.log.debug(f"Delayed submit started for: {song_info['title']}")
        time.sleep(self.settings['min_play_time'])
        self.submit_listen(song_info)

    def on_modified(self, event):
        if event.src_path == self.settings['currentsong_file']:
            self.log.debug("Currentsong file changed, handling update")
            self.handle_song_update(self.parse_currentsong())

    def load_settings(self):
        try:
            with open(os.path.join(os.path.dirname(__file__), 'settings.json'), 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings - {e}")
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

    def cleanup(self):
        if self.listen_cache:
            self.listen_cache.save_cache()


def main():
    scrobbler = None
    observer = None
    
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
        scrobbler.log.info("Received shutdown signal...")
    except Exception as e:
        if scrobbler:
            scrobbler.log.error(f"Fatal error: {str(e)}")
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
