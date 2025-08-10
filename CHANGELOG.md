# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.4] - 2025-08-10
### Added
- Automated installer now enables and restarts the systemd service by default

### Changed
- Atomic cache writes (temporary file + os.replace) to reduce corruption risk
- Cache access is now thread-safe using a lock around append/popleft/appendleft
- Preserved order when re-enqueuing a failed batch
- Normalized playback state to lowercase for consistent "play" checks
- Watchdog compares paths via os.path.realpath and handles on_created events
- Sanitized min_play_time (coerced to integer and clamped to >= 0)
- Adjusted reconnection logs to avoid implying active connectivity checks

## [1.0.3] - 2025-01-03
### Fixed
- Fixed infinite loop bug when invalid listen objects are cached
- Improved error handling to prevent cache corruption

### Added
- Signal handlers for graceful shutdown on SIGTERM/SIGINT
- Token masking in error logs to prevent credential leakage
- Optimized cache I/O with delayed writes to reduce disk operations

### Changed
- Preprocessed filter patterns for better performance
- Enhanced cache management with thread-safe operations

## [1.0.2] - 2025-03-01
### Added
- Smart hybrid cache processing system for efficient offline recovery
- Automatic connection detection with optimized batch processing
- Periodic connection checking to process pending scrobbles faster

### Changed
- Improved cache handling with batch processing for 3+ pending scrobbles
- Enhanced recovery after network interruptions

## [1.0.1] - 2025-02-23
### Changed
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

