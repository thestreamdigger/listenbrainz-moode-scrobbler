# ListenBrainz moOde Scrobbler

Python scripts to integrate the moOde audio player (for Raspberry Pi) with ListenBrainz, enabling automatic scrobbling of played tracks.

## About

This script was developed as a hobby project and a learning exercise in Python programming. It monitors tracks played on the moOde audio player and sends them to ListenBrainz, keeping your listening history up to date.

## Features

- Submits "Listening now..." status updates in real-time.
- Scrobbles tracks after a configurable minimum play time.
- Caches scrobbles when offline and retries automatically.
- Reads track metadata (title, artist, album) from moOde.
- Optional filtering to ignore certain tracks or patterns (radio streams).
- Simple JSON configuration file.

## Requirements

- Raspberry Pi running moOde audio player.
- Python 3.6 or higher.
- ListenBrainz account and API token.

## Installation

### 1. Install Dependencies

Ensure that Python 3.6 or higher is installed on your Raspberry Pi.

### 2. Clone the Repository

```bash
git clone https://github.com/your-username/listenbrainz-moode-scrobbler.git
cd listenbrainz-moode-scrobbler
```

### 3. Set Up a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Required Python Packages

```bash
pip install -r requirements.txt
```

### 5. Configure moOde

Enable moOde to generate the `currentsong.txt` file:

1. Access the moOde web interface.
2. Go to "Configure" > "Audio".
3. Enable the "Metadata file" option, so moOde creates `/var/local/www/currentsong.txt`.

### 6. Configure the Script

1. Rename the example settings file:

```bash
mv src/settings.example.json src/settings.json
```

2. Edit `src/settings.json`:

- Replace `"your_token_here"` with your ListenBrainz API token.
- Adjust other settings as needed.

Example:

```json
{
    "listenbrainz_token": "your_token_here",
    "currentsong_file": "/var/local/www/currentsong.txt",
    "min_play_time": 30,
    "cache_file": "pending_listens.json",
    "features": {
        "enable_listening_now": true,
        "enable_listen": true,
        "enable_cache": true
    },
    "filters": {
        "ignore_patterns": {
            "artist": ["Radio station", "Unknown Artist"],
            "album": [],
            "title": []
        },
        "case_sensitive": false
    },
    "retry": {
        "count": 3,
        "delay": 2
    },
    "logging": {
        "enable": true,
        "level": "INFO",
        "format": "[{level}] {message}"
    }
}
```

⚠️ **Important**: Never share your `settings.json` file as it contains your personal ListenBrainz token.

### 7. Run the Script

You can run the script manually for testing:

```bash
python src/main.py
```

## Running as a Service

To run the scrobbler automatically in the background, set it up as a systemd service:

1. Copy the example service file:
```bash
sudo cp lbms.service.example /etc/systemd/system/lbms.service
```

2. Edit the service file if needed (e.g., to adjust paths):
```bash
sudo nano /etc/systemd/system/lbms.service
```

3. Start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable lbms.service
sudo systemctl start lbms.service
```

You can check the service status and logs with:
```bash
sudo systemctl status lbms.service
sudo journalctl -u lbms.service -f
```

## Notes

- Ensure that the user specified in the service file (`User=pi`) has the necessary permissions to read `/var/local/www/currentsong.txt`.
- If you're using a virtual environment, adjust the `ExecStart` and `Environment` variables accordingly.
- Make sure the script has execute permissions:

```bash
chmod +x src/main.py
```

## Acknowledgments

- This project was created as a fun way to learn more about Python programming and integrating with the ListenBrainz API.
- Thanks to the moOde audio player and ListenBrainz projects for their great software.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.
