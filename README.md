# ListenBrainz moOde Scrobbler

A Python script that integrates the moOde audio player (for Raspberry Pi) with ListenBrainz, providing automatic track scrobbling to keep your listening history continuously updated.

## About

This script monitors the tracks currently playing on moOde and sends them to ListenBrainz. Key functionalities include:

- **Real-time "Now Playing" updates** to ListenBrainz
- **Smart scrobbling** after a configurable minimum play duration
- **Offline caching** with automatic retries
- **Automatic metadata extraction** (title, artist, album)
- **Filtering of radio stations** (optional)
- Flexible retry settings
- Detailed debug logging
- UTF-8 metadata support

---

## Key Features

### Real-time Updates
- Continuously monitors moOde’s metadata file for changes.
- Instantly updates your "Now Playing" status on ListenBrainz.
- Ensures your currently playing track is always displayed on your profile.

### Smart Scrobbling
- Configurable minimum playback time before submitting a scrobble.
- Optional filtering of radio or stream content.
- Precise timestamping for accurate play history.

### Offline Support
- Automatically stores failed submissions locally.
- Retries submissions once the connection is restored.
- Keeps a persistent queue of pending scrobbles.
- Reliable scrobbling even under unstable network conditions.

### Easy Configuration
- JSON-based configuration file for simple customization.
- Adjustable features and behavior.
- Token-based authentication for ListenBrainz.

---

## Prerequisites

- moOde audio player installed on a Raspberry Pi.
- Python 3.6 or later.
- A ListenBrainz account and API token.

---

## Project Structure

```plaintext
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

---

## moOde Configuration

1. Access the moOde web interface.
2. Go to **Configure > Audio**.
3. Enable the **Metadata file** option:
   - This generates `/var/local/www/currentsong.txt`.
   - The script monitors this file for updates.

---

## Installation

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/thestreamdigger/listenbrainz-moode-scrobbler.git
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

---

## Configuration

1. Obtain your ListenBrainz token:
   - Log in to [ListenBrainz](https://listenbrainz.org).
   - Go to **Profile Settings** and copy your token.

2. Configure the `settings.json` file:
   ```json
   {
       "listenbrainz_token": "your_listenbrainz_token",
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

---

## Usage

### Running as a Systemd Service

1. Create a systemd service file:
   ```bash
   sudo nano /etc/systemd/system/listenbrainz-moode.service
   ```

2. Add the following content:
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
   ExecStart=/home/pi/listenbrainz-moode-scrobbler/venv/bin/python3 /src/main.py
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

4. Check the service status:
   ```bash
   sudo systemctl status listenbrainz-moode
   ```

5. View logs:
   ```bash
   sudo journalctl -u listenbrainz-moode -f
   ```

---

## Troubleshooting

### Common Issues

1. **Metadata file not updating:**
   - Confirm that moOde’s metadata file option is enabled.
   - Check file permissions for `/var/local/www/currentsong.txt`.

2. **Token validation failure:**
   - Verify your ListenBrainz token.
   - Check your internet connection.

3. **Scrobbles not appearing:**
   - Ensure the configured minimum play time is sufficient.
   - Verify that the track metadata is complete.

---

## License

This project is licensed under the GNU License. Refer to the [LICENSE](LICENSE) file for details.
