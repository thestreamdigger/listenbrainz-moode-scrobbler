# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
- Removed trivial docstrings, kept only meaningful ones
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
