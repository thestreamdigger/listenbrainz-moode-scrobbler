import time
import json
import os
from collections import deque
from html import unescape
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from liblistenbrainz import ListenBrainz, Listen
from threading import Thread


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
        self.client = ListenBrainz()
        self.settings = self.load_settings()
        self.token = self.settings['listenbrainz_token']
        
        cache_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            self.settings['cache_file']
        )
        
        self.listen_cache = ListenCache(cache_file) if self.settings['features']['enable_cache'] else None
        self.current_song = None
        self.play_start_time = None
        self.retry_count = self.settings['retry']['count']
        self.retry_delay = self.settings['retry']['delay']

    def validate_token(self):
        try:
            self.client.set_auth_token(self.token)
        except Exception as e:
            print(f"[ERROR]  Token validation failed: {e}")
            exit(1)

    def parse_currentsong(self):
        print("[DEBUG]  Starting to parse currentsong file")
        try:
            with open(self.settings['currentsong_file'], 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"[DEBUG]  Read {len(lines)} lines from file")

            song_info = {
                "title": None,
                "artist": None,
                "album": None,
                "state": None
            }

            for line in lines:
                if line.startswith("title="):
                    song_info["title"] = self.clean_text(line.split("=", 1)[1])
                    print(f"[DEBUG]  Found title: {song_info['title']}")
                elif line.startswith("artist="):
                    song_info["artist"] = self.clean_text(line.split("=", 1)[1])
                    print(f"[DEBUG]  Found artist: {song_info['artist']}")
                elif line.startswith("album="):
                    song_info["album"] = self.clean_text(line.split("=", 1)[1])
                    print(f"[DEBUG]  Found album: {song_info['album']}")
                elif line.startswith("state="):
                    song_info["state"] = self.clean_text(line.split("=", 1)[1])
                    print(f"[DEBUG]  Found state: {song_info['state']}")

            if not song_info["title"] or not song_info["artist"]:
                print("[DEBUG]  Incomplete song info detected")
                return None

            print("[DEBUG]  Successfully parsed song info")
            return song_info

        except Exception as e:
            print(f"[ERROR]  Error parsing song information: {str(e)}")
            return None

    def submit_playing_now(self, song_info):
        if not self.settings['features']['enable_listening_now']:
            print("[DEBUG]  Listening Now feature disabled")
            return True

        try:
            print("[DEBUG]  Submitting Now Playing status...")
            listen = Listen(
                track_name=song_info['title'],
                artist_name=song_info['artist'],
                release_name=song_info.get('album', '')
            )
            self.client.submit_playing_now(listen)
            print(f"[OK]     Now Playing: {song_info['title']} by {song_info['artist']}")
            return True
        except Exception as e:
            print(f"[ERROR]  Failed to submit Now Playing: {e}")
            return False

    def submit_listen(self, song_info):
        print("[DEBUG]  Entering submit_listen")
        if not self.settings['features']['enable_listen']:
            print("[DEBUG]  Listen submission disabled")
            return

        current_time = time.time()
        play_time = current_time - self.play_start_time if self.play_start_time else 0
        print(f"[DEBUG]  Calculated play time: {int(play_time)}s")

        if play_time < self.settings['min_play_time']:
            print(f"[INFO]   Song skipped: {song_info['title']} (played for {int(play_time)}s, minimum required: {self.settings['min_play_time']}s)")
            return

        print(f"[DEBUG]  Creating Listen object for submission")
        listen = Listen(
            track_name=song_info['title'],
            artist_name=song_info['artist'],
            release_name=song_info.get('album', ''),
            listened_at=int(current_time)
        )

        for attempt in range(self.retry_count):
            try:
                print(f"[DEBUG]  Attempting submission (attempt {attempt + 1}/{self.retry_count})")
                self.client.submit_single_listen(listen)
                print(f"[INFO]   Listen submitted: {song_info['title']} by {song_info['artist']} ({song_info.get('album', 'N/A')})")
                return
            except Exception as e:
                print(f"[ERROR]  Attempt {attempt + 1}/{self.retry_count} failed: {str(e)}")
                if attempt < self.retry_count - 1:
                    print("[DEBUG]  Waiting before retry")
                    time.sleep(self.retry_delay)

    def clean_text(self, text):
        if not text:
            return ""
        decoded_text = unescape(text)
        return decoded_text.strip()

    def handle_song_update(self, song_info):
        print("[DEBUG]  Processing song update...")
        if not song_info:
            print("[DEBUG]  No song metadata available")
            return

        if self.should_ignore(song_info):
            return

        print(f"[DEBUG]  Current playback state: {song_info.get('state', 'unknown')}")

        if song_info.get("state") != "play":
            print("[DEBUG]  Playback is not in play state")
            if self.current_song:
                print(f"[INFO]   Playback stopped: {self.current_song['title']}")
                print("[DEBUG]  Resetting playback tracking")
                self.current_song = None
                self.play_start_time = None
            return

        if song_info != self.current_song:
            print("[DEBUG]  New track detected")
            if self.settings['features']['enable_listening_now']:
                print("[DEBUG]  Updating Now Playing status")
                self.submit_playing_now(song_info)

            print("[DEBUG]  Starting playback tracking")
            self.play_start_time = time.time()
            self.current_song = song_info

            if self.settings['features']['enable_listen']:
                print("[DEBUG]  Initiating scrobble delay")
                Thread(target=self._delayed_submit, args=(song_info,), daemon=True).start()

    def _delayed_submit(self, song_info):
        print(f"[DEBUG]  Starting delayed submit for: {song_info['title']}")
        time.sleep(self.settings['min_play_time'])
        print(f"[DEBUG]  Delay completed, submitting listen for: {song_info['title']}")
        self.submit_listen(song_info)

    def handle_initial_song(self):
        song_info = self.parse_currentsong()
        if song_info and song_info.get("state") == "play":
            if self.should_ignore(song_info):
                return

            if self.settings['features']['enable_listening_now']:
                self.submit_playing_now(song_info)

            self.current_song = song_info
            self.play_start_time = time.time()

            if self.settings['features']['enable_listen']:
                Thread(target=self._delayed_submit, args=(song_info,), daemon=True).start()

    def on_modified(self, event):
        if event.src_path == self.settings['currentsong_file']:
            print("[DEBUG]  Currentsong file changed, handling update")
            self.handle_song_update(self.parse_currentsong())

    def load_settings(self):
        try:
            with open(os.path.join(os.path.dirname(__file__), 'settings.json'), 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
            return None

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
                print(f"[DEBUG]  Ignoring content: {song_info.get('title')} (matched {field} pattern)")
                return True

        return False

def main():
    scrobbler = ListenBrainzScrobbler()
    
    print("[INFO]   ListenBrainz moOde Scrobbler")
    print("[INFO]   ============================")
 
    print("[WAIT]   Validating ListenBrainz token...")
    scrobbler.validate_token()
    print("[OK]     Token validated successfully")

    scrobbler.handle_initial_song()

    observer = Observer()
    observer.schedule(
        scrobbler, 
        path=os.path.dirname(scrobbler.settings['currentsong_file']), 
        recursive=False
    )
    observer.start()

    try:
        print("[INFO]   Scrobbler is now running. Waiting for updates...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
