# ListenBrainz moOde Scrobbler

[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)](https://github.com/thestreamdigger/listenbrainz-moode-scrobbler)
[![License](https://img.shields.io/badge/license-GPL%20v3-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)]()
[![Raspberry Pi](https://img.shields.io/badge/platform-Raspberry%20Pi-C51A4A.svg)](https://www.raspberrypi.org/)
[![moOde](https://img.shields.io/badge/works%20with-moOde%20audio-orange.svg)](https://moodeaudio.org/)

Python scrobbler for moOde audio player (Raspberry Pi) to ListenBrainz. Watches `currentsong.txt` and submits played tracks.

## About

Hobby project. Monitors tracks played via moOde, submits to ListenBrainz.

Supported sources: MPD (local files, internet radio, UPnP via upmpdcli). Airplay, Spotify Connect and Bluetooth are out of scope — moOde writes only a renderer stub to `currentsong.txt` for those.

## Features

- Real-time "listening now" status
- Canonical scrobble rule: `min(duration * 50%, 240s)`, with 240s
  fallback when duration is missing (stream-like). `min_play_time`
  is a floor in both branches.
- ListenBrainz metadata: `duration_ms`, `release_mbid`, `tracknumber`,
  `submission_client`, `media_player` (per MetaBrainz recommendations)
- Offline cache with automatic retry and batch submission
- Metadata parsing from moOde `currentsong.txt`
- `.env` token storage with automatic redaction in logs
- Pattern filters (ignore radio streams, unknown artists)
- `--dry-run` mode for testing without submission
- JSON configuration

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

**Note:** installer creates `/etc/systemd/system/lbms.service`, enables auto-start on boot, and starts the service. Runs as `$SUDO_USER` (fallback `pi`).

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

Auto-created by installer. Mode `600`, listed in `.gitignore`.

#### 2. `src/settings.json` - Application Settings

Committed to repo (no token). Edit to configure scrobbler behavior:

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
| `min_play_time` | Floor (seconds) under the canonical rule | `30` |
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

Enable `currentsong.txt` output in moOde:

1. Open moOde web UI
2. **Configure** → **Audio** → **MPD options**
3. Enable **Metadata file**

Writes to `/var/local/www/currentsong.txt`. Scrobbler will not see updates if disabled.

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

### Cache Processing

- Individual submission for small queues (< 3 pending)
- Batch submission (up to 10) for larger queues after offline recovery
- Connection re-check every 60s processes pending scrobbles
- Atomic writes (`fsync` + `rename`) on cache save
- Backup (`.corrupt.<timestamp>`) on parse errors

### Content Filtering

Skip scrobbles by pattern:

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

Tracks matching any pattern are skipped.

## Troubleshooting

### Token not found

```
[ERROR] Token not found: env or settings.json
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

**Note:** systemd install runs scrobbler in background. Check with `sudo systemctl status lbms`.

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

## Security

- `.env` gitignored, mode 600
- Token redacted in all log output
- Never hardcode tokens

## Contributing

Contributions welcome: bug reports, features, PRs, docs.

## Acknowledgments

- [moOde audio player](https://moodeaudio.org/) — audio player for Raspberry Pi
- [ListenBrainz](https://listenbrainz.org/) — open-source music tracking
- [python-dotenv](https://github.com/theskumar/python-dotenv) — env var loader

## License

GNU General Public License v3.0. See [LICENSE](LICENSE).
