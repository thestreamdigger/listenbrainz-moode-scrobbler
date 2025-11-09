# ListenBrainz moOde Scrobbler
[![Version](https://img.shields.io/badge/version-1.0.4-blue.svg)](https://github.com/thestreamdigger/listenbrainz-moode-scrobbler)
[![License](https://img.shields.io/badge/license-GPL%20v3-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)]()
[![Raspberry Pi](https://img.shields.io/badge/platform-Raspberry%20Pi-C51A4A.svg)](https://www.raspberrypi.org/)
[![moOde](https://img.shields.io/badge/works%20with-moOde%20audio-orange.svg)](https://moodeaudio.org/)

Python scripts to integrate the moOde audio player (for Raspberry Pi) with ListenBrainz, enabling automatic scrobbling of played tracks.

## About

This script was developed as a hobby project and a learning exercise in Python programming. It monitors tracks played on the moOde audio player and sends them to ListenBrainz, keeping your listening history up to date.

## Features

- Submits "Listening now..." status updates in real-time.
- Scrobbles tracks after a configurable minimum play time.
- Caches scrobbles when offline and retries automatically.
- Intelligent connection recovery with optimized batch processing.
- Reads track metadata (title, artist, album) from moOde.
- Optional filtering to ignore certain patterns (good for radio streams).
- Simple JSON configuration file.


## Requirements

- Raspberry Pi running moOde audio player.
- Python 3.8 or higher.
- ListenBrainz account and API token.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/thestreamdigger/listenbrainz-moode-scrobbler.git lbms
cd lbms
```

### 2. Set Up a Virtual Environment

```bash
# Install python3-venv package if not already installed
sudo apt-get install python3-venv

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Required Python Packages

```bash
# Install project dependencies
pip install -r requirements.txt
```

### 4. Configure moOde

Enable moOde to generate the `currentsong.txt` file:

1. Access the moOde web interface.
2. Go to "Configure" > "Audio".
3. Enable the "Metadata file" option, so moOde creates `/var/local/www/currentsong.txt`.

### 5. Configure the Script

Create and edit `src/settings.json` with your ListenBrainz token and preferences. Example:

```json
{
    // Your ListenBrainz user token (required)
    "listenbrainz_token": "your_token_here",

    // Path to moOde's current song info file
    "currentsong_file": "/var/local/www/currentsong.txt",

    // Minimum seconds a track must play before scrobbling
    "min_play_time": 30,

    // File to store pending scrobbles when offline
    "cache_file": "pending_listens.json",

    // Feature toggles
    "features": {
        "enable_listening_now": true,       // Send "now playing" updates
        "enable_listen": true,              // Enable scrobbling
        "enable_cache": true                // Save failed scrobbles to retry later
    },

    // Content filtering options
    "filters": {
        "ignore_patterns": {
            "artist": ["Radio station", "Unknown Artist"],  // Skip these artists
            "album": [],                    // Skip tracks from these albums
            "title": []                     // Skip tracks with these titles
        },
        "case_sensitive": false             // Case-sensitive pattern matching
    },

    // Network retry settings
    "retry": {
        "count": 3,                         // Number of retry attempts
        "delay": 2                          // Seconds between retries
    },

    // Logging configuration
    "logging": {
        "enable": true,                     // Enable/disable logging
        "level": "INFO",                    // DEBUG, INFO, WARNING, ERROR, CRITICAL
        "format": "[{level}] {message}",    // Log message format
        "timestamp": false                  // Add timestamps to logs
    }
}
```

**Important**: Never share your `settings.json` file as it contains your personal ListenBrainz token.

### 6. Run the Script

You can run the script manually for testing:

```bash
# Make sure your virtual environment is active
source venv/bin/activate

# Run the script
python3 src/main.py
```

Note: The virtual environment must be activated before running the script to ensure all dependencies are available. All commands assume you are in the lbms directory. For automated execution, see the section below.

## Running as a Service

To have the scrobbler run automatically every time moOde starts up, you can set it up as a systemd service. This ensures your scrobbles will be sent automatically without manual intervention after reboots.

1. Copy the example service file:
```bash
sudo cp examples/lbms.service.example /etc/systemd/system/lbms.service
```

2. Edit the service file if needed (e.g., to adjust paths):
```bash
sudo nano /etc/systemd/system/lbms.service
```

3. Configure and start the service (the installer already enables and restarts the service by default):
```bash
# Reload systemd configurations
sudo systemctl daemon-reload

# Enable service to start automatically at boot
sudo systemctl enable lbms.service

# Start/restart the service immediately
sudo systemctl restart lbms.service
```

To disable automatic startup and stop the service:
```bash
# Remove automatic startup at boot
sudo systemctl disable lbms.service

# Stop the service immediately
sudo systemctl stop lbms.service
```

You can check the service status and logs with:
```bash
sudo systemctl status lbms.service
sudo journalctl -u lbms.service -f
```

## Advanced Features

### Smart Cache Processing

The scrobbler includes an intelligent cache system that:

- Processes individual scrobbles in real-time for immediate feedback
- Automatically switches to batch processing when recovering from offline periods
- Periodically checks for connection restoration and processes pending scrobbles
- Optimizes network usage by sending up to 10 scrobbles at once when appropriate

This hybrid approach ensures both real-time accuracy for current listening and efficient recovery after connection issues.

## Notes

- Ensure that the user specified in the service file (`User=pi`) has the necessary permissions to read `/var/local/www/currentsong.txt`.
- If you're using a virtual environment, adjust the `ExecStart` and `Environment` variables accordingly.
- Make sure the script has execute permissions:

```bash
chmod +x src/main.py
```

## Acknowledgments

Thanks to the moOde audio player and ListenBrainz projects for their great software.

## License

This project is free software: you can freely use, modify, and share it. It is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
