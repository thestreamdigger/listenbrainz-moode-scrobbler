# ListenBrainz moOde Scrobbler

A Python script to integrate moOde audio player (for Raspberry Pi) with ListenBrainz, enabling automatic scrobbling of played tracks.

## About

This script monitors tracks played on moOde audio player and sends them to ListenBrainz, keeping your listening history up to date. It supports:

- "Now Playing" status submission
- Track scrobbling after minimum play time
- Local cache for offline listens
- Automatic track metadata reading

## Prerequisites

- moOde audio player installed
- Python 3.6 or higher
- ListenBrainz account and API token

## Project Structure

```
lbms/
├── __init__.py
├── main.py
├── README.md
├── requirements.txt
└── setup.py
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
git clone https://github.com/your-username/listenbrainz-moode-script.git
cd listenbrainz-moode-script
```

2. Install in development mode:
```bash
pip install -e .
```

### Using pip
```bash
pip install listenbrainz-moode-script
```

## Configuration

1. Get your ListenBrainz token:
   - Log in to [ListenBrainz](https://listenbrainz.org)
   - Go to profile settings
   - Copy your token

2. Configure your ListenBrainz token:
   - Open `lbms/main.py` file
   - Replace `LISTENBRAINZ_TOKEN` with your personal token

## Usage

After installation, you can run the script in two ways:

1. Using the installed command:
```bash
listenbrainz-moode
```

2. Using Python module:
```bash
python -m lbms.main
```

The script will:
- Validate your ListenBrainz token
- Start monitoring the metadata file
- Automatically submit played track information

## Settings

In `src/settings.json` you can adjust these settings:

- `min_play_time`: Minimum time (in seconds) before recording a track
- `features`:
  - `enable_listening_now`: Enable/disable "Now Playing" status
  - `enable_listen`: Enable/disable scrobbling
  - `enable_cache`: Enable/disable local cache
  - `ignore_radio`: Enable/disable radio station scrobbling

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
- All contributors and users of this script

## Support

If you encounter any issues or need help, please:
1. Check the Troubleshooting section
2. Look through existing GitHub issues
3. Create a new issue with detailed information about your problem

---

**Note:** This project is DIY and is not officially in any relation with moOde audio or ListenBrainz.
