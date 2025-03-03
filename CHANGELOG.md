# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
- Improved log messages clarity by removing redundant "Track detected" notifications
- Unified logging format for "Listening now..." messages
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

