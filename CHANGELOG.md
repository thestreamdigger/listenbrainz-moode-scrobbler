# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.5] - 2025-11-01
### Changed
- Token now stored in .env file instead of settings.json
- Installation script prompts for token during setup
- Improved documentation with clearer installation instructions
- README and CHANGELOG moved to project root for better visibility

### Added
- Named constants for configuration values
- Documentation for classes and methods
- Detailed documentation about systemd service installation and configuration
- Complete manual installation guide with systemd service setup instructions

### Security
- Credentials protected from version control
- Automatic .env file creation with secure permissions

## [1.0.4] - 2025-10-05
### Changed
- Simplified cache directory structure (src/cache/ instead of nested subdirectory)
- Added debug logging to silent exception handlers for better troubleshooting
- Removed obsolete pending_listens.json from repository

## [1.0.3] - 2025-01-03
### Fixed
- Fixed infinite loop bug when invalid listen objects are cached
- Improved error handling to prevent cache corruption

### Added
- Signal handlers for graceful shutdown on SIGTERM/SIGINT
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

