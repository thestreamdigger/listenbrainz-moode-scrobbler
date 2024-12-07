# ListenBrainz moOde Scrobbler

A Python script to integrate moOde audio player (for Raspberry Pi) with ListenBrainz, enabling automatic scrobbling of played tracks.

## About

This script monitors tracks played on moOde audio player and sends them to ListenBrainz, keeping your listening history up to date. It supports:

- "Now Playing" status submission (real-time updates)
- Track scrobbling after configurable minimum play time
- Local cache for offline listens with automatic retry
- Automatic track metadata reading (title, artist, album)
- Radio station optional filtering
- Configurable retry mechanism for failed submissions
- Detailed debug logging
- Support for UTF-8 encoded metadata

### Key Features

#### Real-time Updates
- Monitors moOde's metadata file for changes
- Instantly updates "Now Playing" status on ListenBrainz
- Shows current track information in your profile

#### Smart Scrobbling
- Configurable minimum play time before scrobbling
- Optional filtering of radio/stream content
- Accurate timestamp recording

#### Offline Support
- Local caching of failed submissions
- Automatic retry when connection is restored
- Persistent storage of pending scrobbles
- Queue management for reliability

#### Easy Configuration
- JSON-based settings file
- Customizable features and behaviors
- Adjustable retry parameters
- Simple token-based authentication

## Prerequisites

- moOde audio player installed
- Python 3.6 or higher
- ListenBrainz account and API token

## Project Structure

```
listenbrainz-moode-scrobbler/
├── LICENSE
├── README.md
├── requirements.txt
├── setup.py
└── src/
    ├── __init__.py
    ├── main.py
    ├── pending_listens.json
    └── settings.json
```

## moOde Configuration

1. Access moOde web interface
2. Go to "Configure" > "Audio"
3. Look for "Metadata file" option
4. Enable this option so moOde generates the `/var/local/www/currentsong.txt` file
   - This file contains current track metadata (title, artist, album, etc.)
   - The script monitors changes to this file to perform scrobbling

## Installation

### From Source
1. Clone this repository:
```bash
git clone https://github.com/your-username/listenbrainz-moode-scrobbler.git
cd listenbrainz-moode-scrobbler
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install in development mode:
```bash
pip install -e .
```

### Using pip
1. Create project directory:
```bash
mkdir listenbrainz-moode-scrobbler
cd listenbrainz-moode-scrobbler
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install via pip:
```bash
pip install listenbrainz-moode-scrobbler
```

## Configuration

1. Get your ListenBrainz token:
   - Log in to [ListenBrainz](https://listenbrainz.org)
   - Go to profile settings
   - Copy your token

2. Configure your settings:
   - Open `src/settings.json`
   - Replace `"your-token-here"` with your personal ListenBrainz token
   - Adjust other settings if needed:
     ```json
     {
         "listenbrainz_token": "your-token-here",
         "currentsong_file": "/var/local/www/currentsong.txt",
         "min_play_time": 30,
         "features": {
             "enable_listening_now": true,
             "enable_listen": true,
             "enable_cache": true,
             "ignore_radio": true
         },
         "filters": {
             "ignore_patterns": {
                 "artist": ["Radio station", "Unknown Artist"],
                 "album": ["radio", "stream", "webradio"],
                 "title": ["commercial break", "station id"]
             },
             "case_sensitive": false
         },
         "retry": {
             "count": 3,
             "delay": 2
         }
     }
     ```

## Settings

The `settings.json` file allows you to customize:

- `listenbrainz_token`: Your personal ListenBrainz API token
- `currentsong_file`: Path to moOde's current song metadata file
- `min_play_time`: Minimum time (in seconds) before recording a track
- `features`:
  - `enable_listening_now`: Enable/disable "Now Playing" status
  - `enable_listen`: Enable/disable scrobbling
  - `enable_cache`: Enable/disable local cache
  - `ignore_radio`: Enable/disable radio station filtering
- `filters`:
  - `ignore_patterns`: Patterns to ignore in metadata fields
    - `artist`: List of artist names to ignore
    - `album`: List of album name patterns to ignore
    - `title`: List of title patterns to ignore
  - `case_sensitive`: Whether pattern matching is case-sensitive
- `retry`:
  - `count`: Number of retry attempts for failed submissions
  - `delay`: Delay (in seconds) between retry attempts

### Content Filtering

The scrobbler can be configured to ignore specific content using pattern matching:

- Configure patterns for each metadata field (artist, album, title)
- Case-sensitive matching is optional
- Multiple patterns can be defined for each field
- Useful for filtering:
  - Radio stations and streams
  - Unknown or generic artists
  - Commercial breaks
  - Station identifications
  - Web radio content

## Usage

### Running as a Service (Recommended)

1. Create a systemd service file:
```bash
sudo nano /etc/systemd/system/listenbrainz-moode.service
```

2. Add the following content (adjust paths as needed):
```ini
[Unit]
Description=ListenBrainz moOde Scrobbler
After=network.target moode.service

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/listenbrainz-moode-scrobbler
Environment=PATH=/home/pi/listenbrainz-moode-scrobbler/venv/bin:$PATH
ExecStart=/home/pi/listenbrainz-moode-scrobbler/venv/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable listenbrainz-moode
sudo systemctl start listenbrainz-moode
```

4. Check service status:
```bash
sudo systemctl status listenbrainz-moode
```

5. View logs:
```bash
sudo journalctl -u listenbrainz-moode -f
```

### Manual Execution (For Testing)

You can also run the script manually in two ways:

1. Using the installed command:
```bash
source venv/bin/activate
listenbrainz-moode
```

2. Using Python module:
```bash
source venv/bin/activate
python -m src.main
```

The script will:
- Validate your ListenBrainz token
- Start monitoring the metadata file
- Automatically submit played track information

### Service Management Commands

- Stop the service:
```bash
sudo systemctl stop listenbrainz-moode
```

- Restart the service:
```bash
sudo systemctl restart listenbrainz-moode
```

- Disable service autostart:
```bash
sudo systemctl disable listenbrainz-moode
```

## Features

### Now Playing Updates
- Real-time updates of currently playing tracks
- Immediate reflection on your ListenBrainz profile

### Scrobbling
- Tracks are scrobbled after the minimum play time
- Includes artist, title, and album information
- Timestamp recording for accurate listening history

### Offline Support
- Local cache for failed submissions
- Automatic retry when connection is restored
- Persistent storage of pending scrobbles

## Troubleshooting

### Common Issues

1. **Metadata file not updating:**
   - Verify moOde's metadata file option is enabled
   - Check file permissions on `/var/local/www/currentsong.txt`

2. **Token validation fails:**
   - Verify your ListenBrainz token is correct
   - Check your internet connection
   - Ensure ListenBrainz service is accessible

3. **Scrobbles not appearing:**
   - Check minimum play time setting
   - Verify track metadata is complete
   - Look for error messages in the script output

## Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest improvements
- Submit pull requests

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [moOde audio player](https://moodeaudio.org/) team
- [ListenBrainz](https://listenbrainz.org/) project
- Members of the moOde audio forum for their support and feedback

## Support

If you encounter any issues or need help, please:
1. Check the Troubleshooting section
2. Look through existing GitHub issues
3. Create a new issue with detailed information about your problem

---

**Note:** This project is DIY and is not officially in any relation with moOde audio or ListenBrainz.
