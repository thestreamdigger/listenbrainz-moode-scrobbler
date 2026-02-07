# ListenBrainz moOde Scrobbler

[![Version](https://img.shields.io/badge/version-1.0.6-blue.svg)](https://github.com/thestreamdigger/listenbrainz-moode-scrobbler)
[![License](https://img.shields.io/badge/license-GPL%20v3-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)]()
[![Raspberry Pi](https://img.shields.io/badge/platform-Raspberry%20Pi-C51A4A.svg)](https://www.raspberrypi.org/)
[![moOde](https://img.shields.io/badge/works%20with-moOde%20audio-orange.svg)](https://moodeaudio.org/)

Python scrobbler to integrate moOde audio player (Raspberry Pi) with ListenBrainz, enabling automatic tracking of played tracks.

## About

This script was developed as a hobby project and a learning exercise in Python programming. It monitors tracks played on the moOde audio player and sends them to ListenBrainz, keeping your listening history up to date.

## Features

- Real-time "Listening now..." status updates
- Automatic track scrobbling with configurable minimum play time
- Offline cache with automatic retry when connection is restored
- Intelligent batch processing for efficient network usage
- Reads track metadata (title, artist, album) from moOde
- Secure credential management with `.env` file
- Optional filtering to ignore certain patterns (e.g., radio streams)
- Simple JSON configuration

## Requirements

- Raspberry Pi running [moOde audio player](https://moodeaudio.org/)
- Python 3.8 or higher
- [ListenBrainz](https://listenbrainz.org/) account and API token

## Quick Installation

The installer will guide you through the setup and ask for your ListenBrainz token:

```bash
# Clone the repository
git clone https://github.com/thestreamdigger/listenbrainz-moode-scrobbler.git lbms
cd lbms

# Run the installer
sudo ./install.sh
```

**That's it!** The installer will:
1. Set up the Python environment
2. Ask for your ListenBrainz token
3. Create all necessary configuration files
4. Install, enable, and start the systemd service (`lbms.service`) - the service will run automatically on boot

### Installation Options

```bash
# Full installation with systemd service (recommended)
# This will install, enable, and start the lbms.service
# The service will automatically start on system boot
sudo ./install.sh

# Install without systemd service (manual execution)
sudo ./install.sh --skip-service

# Skip token configuration (configure later)
sudo ./install.sh --skip-token

# Quiet mode (no interactive prompts)
sudo ./install.sh -q

# Show help
./install.sh --help
```

**Note:** By default, the installer will:
- Create the systemd service file at `/etc/systemd/system/lbms.service`
- Enable the service to start automatically on boot
- Start the service immediately after installation
- The service will run as the user who executed the installer (or `pi` user by default)

## Configuration

### Getting Your ListenBrainz Token

1. Visit [https://listenbrainz.org/settings/](https://listenbrainz.org/settings/)
2. Log in or create an account
3. Copy your "User Token"
4. Paste it when prompted during installation

### Configuration Files

The scrobbler uses two configuration files:

#### 1. `.env` - Secure Credentials (NEVER commit to Git)

Your ListenBrainz token is stored here:

```bash
# .env
LISTENBRAINZ_TOKEN=your_token_here
```

This file is automatically created by the installer when you run `sudo ./install.sh`.

**Security:** The `.env` file is protected with `600` permissions and listed in `.gitignore` to prevent accidental exposure.

#### 2. `src/settings.json` - Application Settings (Included)

This file is included in the repository and contains all application settings (no token).
Configure scrobbler behavior by editing this file:

```json
{
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
        "format": "[{level}] {message}",
        "timestamp": true
    }
}
```

**Configuration Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `currentsong_file` | Path to moOde's current song file | `/var/local/www/currentsong.txt` |
| `min_play_time` | Minimum seconds before scrobbling | `30` |
| `cache_file` | File to store pending scrobbles | `pending_listens.json` |
| `enable_listening_now` | Send "now playing" updates | `true` |
| `enable_listen` | Enable scrobbling | `true` |
| `enable_cache` | Cache failed submissions | `true` |
| `ignore_patterns` | Patterns to skip (artist/album/title) | `[]` |
| `case_sensitive` | Case-sensitive pattern matching | `false` |
| `retry.count` | Number of retry attempts | `3` |
| `retry.delay` | Seconds between retries | `2` |
| `logging.level` | Log level (DEBUG/INFO/WARNING/ERROR) | `INFO` |

### moOde Configuration

Enable moOde to generate the `currentsong.txt` file:

1. Access the moOde web interface
2. Go to **Configure** → **System** → **Local Services**
3. Enable **Metadata file** option
4. This creates `/var/local/www/currentsong.txt` with track information

## Usage

### With Systemd Service (Recommended)

If installed with systemd service:

```bash
# Check status
sudo systemctl status lbms

# Start/stop/restart
sudo systemctl start lbms
sudo systemctl stop lbms
sudo systemctl restart lbms

# View real-time logs
sudo journalctl -u lbms -f

# View recent logs
sudo journalctl -u lbms -n 50
```

### Manual Execution

Run the scrobbler manually:

```bash
# Using virtual environment
./venv/bin/python3 src/main.py

# Or activate environment first
source venv/bin/activate
python3 src/main.py
```

## Advanced Features

### Smart Cache Processing

The scrobbler includes an intelligent cache system:

- **Real-time processing:** Individual scrobbles submitted immediately for instant feedback
- **Batch processing:** Automatically switches to batches (up to 10 scrobbles) when recovering from offline periods
- **Periodic checks:** Monitors connection every 60 seconds and processes pending scrobbles
- **Optimized I/O:** Delayed writes reduce disk operations

This hybrid approach ensures both real-time accuracy and efficient recovery after connection issues.

### Content Filtering

Filter out unwanted scrobbles using patterns:

```json
{
    "filters": {
        "ignore_patterns": {
            "artist": ["Radio station", "Unknown Artist", "Various Artists"],
            "album": ["Compilation", "Live Stream"],
            "title": ["Advertisement", "Station ID"]
        },
        "case_sensitive": false
    }
}
```

Tracks matching any pattern will be skipped.

## Troubleshooting

### Token not found

```
ERROR: LISTENBRAINZ_TOKEN not found in environment or settings.json
```

**Solution:**
```bash
# Check if .env exists
ls -la .env

# If not, create it manually
nano .env
# Add: LISTENBRAINZ_TOKEN=your_token_here
chmod 600 .env
```

### Permission denied

**Solution:**
```bash
# Fix permissions
sudo chown -R pi:pi /home/pi/lbms
chmod 600 .env
chmod 600 src/settings.json
```

### Service not starting

**Solution:**
```bash
# Check service status
sudo systemctl status lbms

# View detailed logs
sudo journalctl -u lbms -n 100

# Restart service
sudo systemctl restart lbms
```

### Testing the .env file

```bash
# Run test script
python test_env.py
```

## Manual Installation

If you prefer manual setup without the installer:

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file manually
echo "LISTENBRAINZ_TOKEN=your_token_here" > .env

# 4. Set permissions
chmod 600 .env
chmod 600 src/settings.json

# 5. (Optional) Install systemd service
# Replace /home/pi/lbms with your actual installation path
# Also update User and Group if not using 'pi' user
sudo cp examples/lbms.service.example /etc/systemd/system/lbms.service
sudo sed -i "s|/home/pi/lbms|$(pwd)|g" /etc/systemd/system/lbms.service
# If your user is not 'pi', also run:
# sudo sed -i "s|User=pi|User=$USER|g" /etc/systemd/system/lbms.service
# sudo sed -i "s|Group=pi|Group=$USER|g" /etc/systemd/system/lbms.service
sudo systemctl daemon-reload
sudo systemctl enable lbms.service
sudo systemctl start lbms.service

# 6. Run the scrobbler (if not using systemd service)
python3 src/main.py
```

**Note:** If you install the systemd service (step 5), the scrobbler will run automatically in the background. You can check its status with `sudo systemctl status lbms`.

## Project Structure

```
lbms/
├── .env                      # Your token (created by installer, gitignored)
├── .gitignore                # Protects .env from Git
├── install.sh                # Automated installer
├── requirements.txt          # Python dependencies
├── LICENSE                   # GPL v3 license
├── README.md                 # This file
├── CHANGELOG.md              # Version history
├── examples/
│   └── lbms.service.example  # Systemd service template
└── src/
    ├── main.py               # Main scrobbler script
    ├── logger.py             # Logging module
    ├── __version__.py        # Version information
    ├── settings.json         # Application settings (safe to commit)
    └── cache/                # Created at runtime (gitignored)
        └── pending_listens.json  # Offline cache
```

## Documentation

- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes
- **[LICENSE](LICENSE)** - GPL v3 license details

## Security Best Practices

- Keep `.env` file secure (never commit to Git)
- Never hardcode tokens in code
- Never share your token publicly

## Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests
- Improve documentation

## Acknowledgments

- [moOde audio player](https://moodeaudio.org/) - Excellent audio player for Raspberry Pi
- [ListenBrainz](https://listenbrainz.org/) - Open-source music tracking service
- [python-dotenv](https://github.com/theskumar/python-dotenv) - Environment variable management

## License

This project is free software licensed under the **GNU General Public License v3.0**.

You can freely use, modify, and share this software. See the [LICENSE](LICENSE) file for details.

---

**Made with ❤️ for the moOde and ListenBrainz communities**

