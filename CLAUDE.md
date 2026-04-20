# lbms

ListenBrainz moOde Scrobbler v1.1.0.
Tracks played music from moOde audio player to ListenBrainz.

## Target

Raspberry Pi (Linux), Python 3.8+, moOde.

## Features

- Real-time "listening now" status updates
- Automatic scrobbling with configurable minimum play time (30s default)
- Offline cache with automatic retry
- Pattern filtering (ignore radio streams, unknown artists)
- Reads metadata from moOde currentsong file

## Config

`src/settings.json`: currentsong path, min play time, cache file, filters, retry, logging.
Credentials: `.env` file (ListenBrainz token).

## Service

`lbms.service` (systemd). Install: `./install.sh`.

## Status

Maintained.
