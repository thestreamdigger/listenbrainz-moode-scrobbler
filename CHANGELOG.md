# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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

## [1.0.4] - 2025-10-05
### Added
- Debug logging to silent exception handlers for better troubleshooting

### Fixed
- Simplified cache directory structure (src/cache/ instead of nested subdirectory)
- Removed obsolete pending_listens.json from repository

## [1.0.3] - 2025-01-03
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

## [1.0.0] - 2025-10-20
### Added
- Initial stable release
- Real-time "Listening now..." status updates
- Configurable track scrobbling with minimum play time
- Offline caching system with automatic retries
- Track metadata parsing from moOde audio player
- Pattern-based content filtering
- Customizable logging system
