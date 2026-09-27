# lbms

ListenBrainz moOde Scrobbler (version: `src/__version__.py`).
Tracks played music from moOde audio player to ListenBrainz.
The only PUBLIC repo of the account (github.com/thestreamdigger/listenbrainz-moode-scrobbler):
real users clone it, so every change ships with the CHANGELOG, the README and green tests.

## Target

Raspberry Pi (Linux), Python 3.10+, moOde (renderer metadata needs 10.2+).

## Layout

- `src/main.py`: entry, watcher, signals, API transport (User-Agent + timeout)
- `src/currentsong.py`: currentsong.txt parser -> `Song`
- `src/scrobbler.py`: play-session state machine, Listening now, submission
- `src/cache.py`: offline listen cache
- `src/settings.json`: behaviour; token lives in `.env` only

## Tests

```bash
wsl -d Debian -- bash -lc "cd /mnt/c/dev/maintain/lbms && <venv>/bin/python -m unittest discover tests"
```

Run on 3.10 (the floor: `uv venv -p 3.10`) and on the current Python. Linux only (inotify).

## Service

`lbms.service` (systemd). Install and update: `sudo ./install.sh` (`-q` keeps `.env`, restarts).

## Key Learnings

- **moOde rewrites currentsong.txt IN PLACE by default.** The worker writes
  `/tmp/currentsong.txt` and `rename()`s it, but tmp2ram (default on) makes
  `/tmp` a tmpfs, the rename crosses devices, and PHP falls back to
  truncate + write on the SAME inode. `on_modified` therefore fires on an
  empty or half-written file. Trigger on IN_CLOSE_WRITE (`FileClosedEvent`),
  plus create/move for the tmp2ram-off case (an unpaired IN_MOVED_TO arrives
  as `FileCreatedEvent`). moOde's own lcd-updater waits on `close_write`.
- **currentsong.txt is only written with "Metadata file" ON** (Audio >
  MPD Options), default OFF. Rewritten every ~3s while playing (elapsed).
- **Keys (MPD mode):** file, artist, album, title, coverurl, track, date,
  composer, encoded, bitrate, outrate, volume, mute, state, elapsed,
  duration (integer seconds; 0 for radio). Values are htmlspecialchars-
  escaped. There is NO musicbrainz_* key: do not add fields moOde never writes.
- **Renderer mode has no state=.** `file=<Name> Active`; only AirPlay and
  Spotify carry metadata, and only while ALSA is open, so no metadata =
  paused. Durations are in moOde's aplmeta.json / spotmeta.json (ms). Every
  other renderer (Qobuz since 10.3.4, was Deezer) is a marker only.
- **liblistenbrainz 0.7.0 sends no User-Agent and sets no timeout**; the API
  requires a UA and a stalled POST blocked forever. It mounts a module-level
  `adapter` per request: `main.Transport` replaces it. Re-check on upgrade
  (tests/TransportTest proves both, and was proven able to fail).
- **The Pi's wall clock is wrong until NTP syncs.** No RTC: it boots on
  fake-hwclock (last shutdown time) and jumps forward later, days if it was
  off for days (adam, 2026-09-27: journal went Sep 20 23:44 -> Sep 27 00:46
  inside one process). Durations use `time.monotonic()`; wall time is taken
  as late as possible (listened_at is derived at submission).
- **A class with `__len__` is falsy when empty.** `if self.cache:` read an
  empty cache as "cache disabled" and dropped listens. Use `is not None`.
- **f-strings with nested same quotes are 3.12+ only** (PEP 701); the floor
  is 3.10 (moOde 9 is Bookworm = 3.11). The 3.10 test run catches it.
- **Pre-rewrite history lives in the fork** arthurlutz/listenbrainz-moode-scrobbler
  (history here was squashed 2026-02); it is what dated 1.0.0/1.0.3/1.0.4.

## Status

Maintained.
