# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.4.0] - 2026-09-27
### Added
- AirPlay/Spotify pause detection: moOde drops renderer metadata from
  currentsong.txt while no audio flows; read as pause (timer stops, played
  time kept) instead of a session that kept counting
- Renderer track duration read from moOde's aplmeta.json / spotmeta.json
  when they describe the same track: the canonical rule now applies to
  AirPlay/Spotify (was the min_play_time fallback, i.e. 30s)
- Listening now cleared on pause and stop (POST /1/playing-now/delete,
  ListenBrainz 2026-03) and restored on resume
- User-Agent `lbms/<version> ( repo url )` on every API call: ListenBrainz
  requires one and liblistenbrainz 0.7.0 sends none
- HTTP timeout (10s connect / 30s read): liblistenbrainz 0.7.0 sets none, so
  a stalled connection blocked its thread forever, the file watcher included
- Test suite (tests/, stdlib unittest): parser, cache, sessions, transport
  against a local HTTP server, watcher under both moOde write modes

### Changed
- Listen delay counts accumulated play time across pauses (each resume
  restarted the full delay); listened_at stays the first start
- Watcher reacts to close-after-write, create and move (was modify): with
  moOde's default tmp2ram the file is rewritten in place, and modify fired
  on an empty or half-written file
- Qobuz, Squeezelite, Roon Bridge, Bluetooth and inputs end the running MPD
  session: a track cut short by a renderer takeover was scrobbled anyway
- Token validated in the background: an unreachable API delayed startup by
  up to 60s with the watcher not yet running; an invalid token still exits
- Cache drains fully each cycle in batches of 50 (was 10 per minute), runs
  at startup, and is saved on every change (debounce timer removed)
- Cache: a listen refused as invalid (HTTP 400) is isolated from its batch
  and dropped instead of blocking the queue forever
- Errors from the API are logged with their HTTP status
- Code split into currentsong.py, scrobbler.py, cache.py and main.py;
  dataclasses, type hints, match on play state
- Watcher death exits 1 so systemd restarts it (process used to idle on)
- install.sh: checks Python 3.10+ and python3-venv (was an unused pip3
  check), runs commands without eval, restarts the service on reinstall
  (start was a no-op on update), README documents the update path
- Dependencies: python-dotenv 1.2.2 -> 1.2.3; requests pinned (imported)
- README badges follow the family standard (version, license, platform,
  language, domain)

### Fixed
- listened_at survives a wall-clock jump: a Pi boots on fake-hwclock and
  NTP can move the clock days forward mid-track (seen on a live unit: boot
  at Sep 20, synced to Sep 27). The start is kept monotonic and converted
  at submission, so a track autoplayed at boot is no longer dated days back
- systemd unit installed mode 600 (inherited from mktemp by cp), so
  `systemctl cat lbms` failed for the service user; now 644
- Dry run no longer submits the offline cache
- A log format error printed the message unredacted
- Dates of 1.0.0, 1.0.3 and 1.0.4, checked against the original history

### Removed
- release_mbid from musicbrainz_albumid: moOde never writes that key

## [1.3.3] - 2026-09-06
### Fixed
- Track matched by ignore_patterns now closes the previous play session:
  the old track's listen timer no longer fires after the switch (phantom
  scrobble of a track cut short), and replaying that track is detected
  again (was silently skipped: stale current_song + play_start_time)
- Shutdown deadlock: signal handler logged while the main thread could be
  holding the logger lock (startup window), hanging until systemd SIGKILL;
  handler now only records the signal, logger lock made reentrant
- install.sh uses absolute paths for venv and requirements (venv landed in
  the caller's cwd when invoked from outside the repo dir)
- install.sh -q no longer prompts for the token: keeps an existing .env or
  skips with a notice (was blocking on read under non-interactive deploy)
- Cache: invalid listens dropped from a batch now schedule a save; "Cache
  done" only when the queue is empty ("Cache batch done" otherwise)

### Removed
- Unreachable KeyboardInterrupt handler (SIGINT already routed through the
  signal handler)
- Unused PROJECT_DESC in install.sh; CRITICAL logger level without method;
  always-true cache_dir guards in ListenCache
- chmod 600 on settings.json (holds no secret since 1.3.2); redundant sudo
  inside the root-only installer

## [1.3.2] - 2026-07-05
### Fixed
- install.sh now rewrites User=/Group= in the systemd unit to the invoking
  user (was left as pi while config files were chowned mode 600 to
  $SUDO_USER, breaking service start on non-pi installs)
- Unit rewrite is CRLF-proof: sed strips \r before matching, service example
  normalized to LF and pinned via .gitattributes (rsync from Windows
  preserves CRLF, which silently defeated the User=/Group= anchors)

### Removed
- Undocumented listenbrainz_token fallback from settings.json; .env is the
  single token path, matching the README Security section
- Dead currentsong fields from parser: date, composer, bitrate, encoded
  (parsed but never used; same cleanup as 'genre' in 1.2.1)

## [1.3.1] - 2026-06-09
### Changed
- Log and docs use ListenBrainz term "Listening now" (was "Now playing")

## [1.3.0] - 2026-06-09
### Added
- AirPlay and Spotify Connect scrobbling: moOde 10.2+ writes renderer
  artist/album/title to currentsong.txt (file=AirPlay Active / Spotify
  Active, no state line); these are now treated as playing
- media_player reflects source (AirPlay / Spotify / MPD); music_service
  set to spotify.com for Spotify listens

### Compatibility
- Renderer sessions carry no state or duration: pause is not detectable
  (min_play_time timer keeps running) and listens use the min_play_time
  fallback delay
- moOde post-10.2.2 (upstream 1b6812b8) adds duration= to the MPD branch
  of currentsong.txt — the canonical rule min(duration*0.5, 240s) becomes
  fully active with that release, no lbms change needed

## [1.2.2] - 2026-06-09
### Fixed
- Duplicate scrobble on pause/resume: pause no longer discards track state;
  resume re-arms the listen timer only if the play session has not scrobbled yet
- listened_at now reports play start time instead of submission time
  (was shifted by up to 240s on long tracks)
- Invalid cached listen no longer wedges small-queue processing forever
  (dropped with log, matching batch path behavior)

### Changed
- install.sh token prompt no longer echoes token to terminal (read -s)
- settings.json repo default log level reverted to INFO (was DEBUG)
- Version string removed from main.py header comment (single source: __version__.py)

## [1.2.1] - 2026-06-05
### Changed
- Dependencies updated: liblistenbrainz 0.6.1 -> 0.7.0, python-dotenv 1.0.1 -> 1.2.2 (watchdog stays 6.0.0)
- Minimum Python raised to 3.10 (python-dotenv 1.2.2 requirement)
- systemd unit waits for network-online.target (avoids failed start before connectivity)
- README clarifies duration_ms/release_mbid are sent only when present in currentsong.txt

### Removed
- Dead 'genre' field from currentsong parser (parsed but never used; moOde does not emit it)

## [1.2.0] - 2026-04-18
### Added
- Canonical scrobble rule: min(duration * 0.5, 240s), floor at min_play_time
- submission_client, submission_client_version, media_player in additional_info
- duration_ms forwarded when present
- release_mbid forwarded from musicbrainz_albumid when present
- on_moved handler for atomic rename writes to currentsong.txt
- Token redaction in logger across all log levels
- --dry-run flag
- --version flag

### Changed
- Log style aligned (terse, colon for values, err suffix)
- load_dotenv uses explicit path relative to file location
- _delayed_submit validates current track + play_start before submitting
- submit_listen aborts retry loop on shutdown and falls back to cache
- Connection check thread uses Event.wait for interruptible shutdown
- Cached listens use the same payload shape as live submissions

### Fixed
- Data loss in process_pending_listens small_queue: items after first
  failure were drained but not re-enqueued
- Durability gap on atomic cache write (fsync on file and parent dir)
- Corrupted cache no longer silently destroyed (backed up as .corrupt.<ts>)

## [1.1.0] - 2026-02-07
### Changed
- Song identity comparison uses only title/artist/album (prevents duplicate scrobbles)
- Currentsong parser refactored to field mapping (replaces if/elif chain)
- Signal handler uses closure instead of global variable
- Settings access standardized to direct key access
- Cache save split into locked/unlocked variants (fixes load_cache deadlock path)

### Fixed
- Race condition: delayed submit now captures play_start_time at spawn time
- Thread-safe access to pending_listens via has_pending() method
- Track number preserved in cached failed submissions
- Removed redundant feature flag check in submit_playing_now

## [1.0.7] - 2025-12-22
### Changed
- Code style consistency (imports, error handling, dict access)
- Token attribute now private (_token)

### Fixed
- Syntax error in error logging
- Exception handling uses specific exceptions instead of exit()

## [1.0.6] - 2025-11-30
### Added
- Track number metadata in listen submissions
- Optional metadata field parsing (track, date, composer, genre, duration, bitrate, format)

### Fixed
- Enhanced metadata extraction from moOde currentsong.txt
- Standardized internal methods with private naming convention
- Removed code duplication in track extraction and event handling
- Simplified docstrings and removed verbose comments

## [1.0.5] - 2025-11-01
### Added
- Named constants for configuration values
- Documentation for classes and methods
- Detailed documentation about systemd service installation and configuration
- Complete manual installation guide with systemd service setup instructions

### Fixed
- Token now stored in .env file instead of settings.json
- Installation script prompts for token during setup
- Improved documentation with clearer installation instructions
- README and CHANGELOG moved to project root for better visibility
- Credentials protected from version control
- Automatic .env file creation with secure permissions

## [1.0.4] - 2025-08-10
### Added
- Debug logging to silent exception handlers for better troubleshooting

### Fixed
- Simplified cache directory structure (src/cache/ instead of nested subdirectory)
- Removed obsolete pending_listens.json from repository

## [1.0.3] - 2025-06-25
### Added
- Signal handlers for graceful shutdown on SIGTERM/SIGINT
- Optimized cache I/O with delayed writes to reduce disk operations

### Fixed
- Fixed infinite loop bug when invalid listen objects are cached
- Improved error handling to prevent cache corruption
- Preprocessed filter patterns for better performance
- Enhanced cache management with thread-safe operations

## [1.0.2] - 2025-03-01
### Added
- Smart hybrid cache processing system for efficient offline recovery
- Automatic connection detection with optimized batch processing
- Periodic connection checking to process pending scrobbles faster

### Fixed
- Improved cache handling with batch processing for 3+ pending scrobbles
- Enhanced recovery after network interruptions

## [1.0.1] - 2025-02-23
### Fixed
- Code cleanup and optimization in main.py

## [1.0.0] - 2024-12-01
### Added
- Initial stable release
- Real-time "Listening now..." status updates
- Configurable track scrobbling with minimum play time
- Offline caching system with automatic retries
- Track metadata parsing from moOde audio player
- Pattern-based content filtering
- Customizable logging system
