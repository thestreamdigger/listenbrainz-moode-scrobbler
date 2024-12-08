# ListenBrainz moOde Scrobbler

A Python script to integrate moOde audio player (for Raspberry Pi) with ListenBrainz, enabling automatic scrobbling of played tracks.

## About

This script monitors tracks played on moOde audio player and sends them to ListenBrainz, keeping your listening history up to date. Key features include:

- **"Now Playing" status submission** (real-time updates)
- **Track scrobbling** after configurable minimum play time
- **Offline support** with local cache and automatic retry
- **Automatic track metadata reading** (title, artist, album)
- **Radio station filtering** (optional)
- Configurable retry mechanism
- Detailed debug logging
- UTF-8 metadata support

---

## Key Features

### Real-time Updates
- Monitors moOde's metadata file for changes.
- Instantly updates "Now Playing" status on ListenBrainz.
- Reflects current track information on your profile.

### Smart Scrobbling
- Configurable minimum play time before scrobbling.
- Optional filtering for radio or stream content.
- Accurate timestamp recording.

### Offline Support
- Local caching of failed submissions.
- Automatic retry when connection is restored.
- Persistent storage of pending scrobbles.
- Reliable queue management.

### Easy Configuration
- JSON-based settings file.
- Adjustable features and behaviors.
- Simple token-based authentication.

---

## Prerequisites

- moOde audio player installed.
- Python 3.6 or higher.
- ListenBrainz account and API token.

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
2. Navigate to **Configure > Audio**.
3. Enable the **Metadata file** option:
   - Generates `/var/local/www/currentsong.txt`.
   - The script monitors this file for metadata updates.

---

## Installation

### From Source
<<<<<<< HEAD

1. Clone the repository:
   ```bash
   git clone https://github.com/thestreamdigger/listenbrainz-moode-scrobbler.git
   cd listenbrainz-moode-scrobbler
   ```
=======
1. Clone this repository:
```bash
git clone https://github.com/thestreamdigger/listenbrainz-moode-scrobbler.git
cd listenbrainz-moode-scrobbler
```
>>>>>>> 4608a91060d28af15707af71b44d90673b28ee32

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install in development mode:
   ```bash
   pip install -e .
   ```

<<<<<<< HEAD
---

=======
>>>>>>> 4608a91060d28af15707af71b44d90673b28ee32
## Configuration

1. Retrieve your ListenBrainz token:
   - Log in to [ListenBrainz](https://listenbrainz.org).
   - Access **Profile Settings** and copy your token.

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

### Running as a Service (Recommended)

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
   - Confirm moOde metadata file option is enabled.
   - Check file permissions on `/var/local/www/currentsong.txt`.

2. **Token validation fails:**
   - Verify your ListenBrainz token.
   - Check your internet connection.

3. **Scrobbles not appearing:**
   - Verify minimum play time.
   - Ensure metadata is complete.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

For help:
1. Check the **Troubleshooting** section.
2. Review existing GitHub issues.
3. Create a new issue with detailed information.
