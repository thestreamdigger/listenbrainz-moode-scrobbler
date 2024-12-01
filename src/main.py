import time
import json
import os
from collections import deque
from html import unescape
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from liblistenbrainz import ListenBrainz, Listen
from threading import Thread

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pending_listens.json')


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


def load_settings():
    settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
    try:
        with open(settings_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Settings file not found. Please create a 'settings.json' file in the 'src' directory.")
        exit(1)
    except json.JSONDecodeError:
        print("Error parsing 'settings.json'. Please ensure it is valid JSON.")
        exit(1)


class ListenBrainzScrobbler(FileSystemEventHandler):
    def __init__(self):
        print("DEBUG - Initializing ListenBrainzScrobbler")
        self.settings = load_settings()
        self.client = ListenBrainz()
        self.token = self.settings["listenbrainz_token"]
        self.currentsong_file = self.settings["currentsong_file"]
        self.min_play_time = self.settings["min_play_time"]
        self.listen_cache = ListenCache(CACHE_FILE) if self.settings["features"]["enable_cache"] else None
        self.current_song = None
        self.play_start_time = None
        self.retry_count = self.settings["retry"]["count"]
        self.retry_delay = self.settings["retry"]["delay"]

        self.validate_settings()

    def validate_settings(self):
        if not self.token:
            print("ListenBrainz token is not set in 'settings.json'. Please provide a valid token.")
            exit(1)

    def validate_token(self):
        try:
            self.client.set_auth_token(self.token)
            print("Token validated successfully. Connection to ListenBrainz is active.")
        except Exception as e:
            print("Token validation failed! Please check your ListenBrainz token.")
            exit(1)

    def submit_playing_now(self, song_info):
        print("DEBUG - Entering submit_playing_now")
        if not self.settings["features"]["enable_listening_now"]:
            print("DEBUG - Listening Now disabled, skipping")
            return True

        try:
            listen = Listen(
                track_name=song_info['title'],
                artist_name=song_info['artist'],
                release_name=song_info.get('album', '')
            )
            print(f"DEBUG - Created Listen object for Listening Now: {song_info['title']}")

            self.client.submit_playing_now(listen)
            print(f"Listening Now: {song_info['title']} by {song_info['artist']} ({song_info.get('album', 'N/A')})")
            return True
        except Exception as e:
            print(f"DEBUG - Error in submit_playing_now: {str(e)}")
            return False

    def submit_listen(self, song_info):
        print("DEBUG - Entering submit_listen")
        if not self.settings["features"]["enable_listen"]:
            print("DEBUG - Listen submission disabled")
            return

        current_time = time.time()
        play_time = current_time - self.play_start_time if self.play_start_time else 0
        print(f"DEBUG - Calculated play time: {int(play_time)}s")

        if play_time < self.min_play_time:
            print(f"Song skipped: {song_info['title']} (played for {int(play_time)}s, minimum required: {self.min_play_time}s)")
            return

        print(f"DEBUG - Creating Listen object for submission")
        listen = Listen(
            track_name=song_info['title'],
            artist_name=song_info['artist'],
            release_name=song_info.get('album', ''),
            listened_at=int(current_time)
        )

        for attempt in range(self.retry_count):
            try:
                print(f"DEBUG - Attempting submission (attempt {attempt + 1}/{self.retry_count})")
                self.client.submit_single_listen(listen)
                print(f"Listen submitted: {song_info['title']} by {song_info['artist']} ({song_info.get('album', 'N/A')})")
                return
            except Exception as e:
                print(f"Attempt {attempt + 1}/{self.retry_count} failed: {str(e)}")
                if attempt < self.retry_count - 1:
                    print("DEBUG - Waiting before retry")
                    time.sleep(self.retry_delay)

    def clean_text(self, text):
        if not text:
            return ""
        decoded_text = unescape(text)
        return decoded_text.strip()

    def parse_currentsong(self):
        print("DEBUG - Starting to parse currentsong file")
        try:
            with open(self.currentsong_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"DEBUG - Read {len(lines)} lines from file")

            song_info = {
                "title": None,
                "artist": None,
                "album": None,
                "state": None
            }

            for line in lines:
                if line.startswith("title="):
                    song_info["title"] = self.clean_text(line.split("=", 1)[1])
                    print(f"DEBUG - Found title: {song_info['title']}")
                elif line.startswith("artist="):
                    song_info["artist"] = self.clean_text(line.split("=", 1)[1])
                    print(f"DEBUG - Found artist: {song_info['artist']}")
                elif line.startswith("album="):
                    song_info["album"] = self.clean_text(line.split("=", 1)[1])
                    print(f"DEBUG - Found album: {song_info['album']}")
                elif line.startswith("state="):
                    song_info["state"] = self.clean_text(line.split("=", 1)[1])
                    print(f"DEBUG - Found state: {song_info['state']}")

            if not song_info["title"] or not song_info["artist"]:
                print("DEBUG - Incomplete song info detected")
                return None

            print("DEBUG - Successfully parsed song info")
            return song_info

        except Exception as e:
            print(f"DEBUG - Error parsing song information: {str(e)}")
            return None

    def handle_song_update(self, song_info):
        print("DEBUG - Entering handle_song_update")
        if not song_info:
            print("DEBUG - No song info provided")
            return

        print(f"DEBUG - Processing state: {song_info.get('state', 'unknown')}")

        if song_info.get("state") != "play":
            print("DEBUG - State is not 'play'")
            if self.current_song:
                print(f"Playback paused/stopped: {self.current_song['title']}")
                print("DEBUG - Resetting current song and play time")
                self.current_song = None
                self.play_start_time = None
            return

        if song_info != self.current_song:
            print("DEBUG - New song detected")
            if self.settings["features"]["enable_listening_now"]:
                print("DEBUG - Submitting Listening Now")
                self.submit_playing_now(song_info)

            print("DEBUG - Updating play start time and current song")
            self.play_start_time = time.time()
            self.current_song = song_info

            if self.settings["features"]["enable_listen"]:
                print("DEBUG - Starting delayed submit thread")
                Thread(target=self._delayed_submit, args=(song_info,), daemon=True).start()

    def _delayed_submit(self, song_info):
        print(f"DEBUG - Starting delayed submit for: {song_info['title']}")
        time.sleep(self.min_play_time)
        print(f"DEBUG - Delay completed, submitting listen for: {song_info['title']}")
        self.submit_listen(song_info)

    def handle_initial_song(self):
        song_info = self.parse_currentsong()
        if song_info and song_info.get("state") == "play":
            if self.settings["features"]["enable_listening_now"]:
                self.submit_playing_now(song_info)

            self.current_song = song_info
            self.play_start_time = time.time()

            if self.settings["features"]["enable_listen"]:
                Thread(target=self._delayed_submit, args=(song_info,)).start()

    def on_modified(self, event):
        print("DEBUG - File modification detected")
        if event.src_path == self.currentsong_file:
            print("DEBUG - Currentsong file changed, handling update")
            self.handle_song_update(self.parse_currentsong())


def main():
    print("\nlistenbrainz-moode-scrobbler")
    print("============================\n")

    scrobbler = ListenBrainzScrobbler()
    print("Establishing connection...")
    scrobbler.validate_token()

    scrobbler.handle_initial_song()

    event_handler = FileSystemEventHandler()
    event_handler.on_modified = scrobbler.on_modified
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(scrobbler.currentsong_file), recursive=False)
    observer.start()

    try:
        print("Scrobbler is now running. Waiting for updates...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
