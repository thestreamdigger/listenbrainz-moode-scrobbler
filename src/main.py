#!/usr/bin/env python3
#
# ListenBrainz moOde Scrobbler
# Copyright (C) 2024-2026 StreamDigger
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import argparse
import json
import os
import signal
import sys
from pathlib import Path
from threading import Event, Thread

from dotenv import load_dotenv
from liblistenbrainz import ListenBrainz
from liblistenbrainz import client as lb_client
from liblistenbrainz.errors import InvalidAuthTokenException
from requests.adapters import HTTPAdapter
from watchdog.events import FileClosedEvent, FileCreatedEvent, FileMovedEvent, FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from __version__ import __version__
from cache import ListenCache, describe
from currentsong import read
from logger import Logger
from scrobbler import Scrobbler

SRC = Path(__file__).resolve().parent
HTTP_TIMEOUT = (10, 30)
CACHE_INTERVAL = 60
USER_AGENT = f"lbms/{__version__} ( https://github.com/thestreamdigger/listenbrainz-moode-scrobbler )"


class Transport(HTTPAdapter):
    """liblistenbrainz 0.7.0 sends no User-Agent (the API requires one) and
    no timeout (a stalled connection blocks its caller forever). It mounts a
    module-level adapter on every request; replacing it fixes both."""

    def send(self, request, **kwargs):
        request.headers['User-Agent'] = USER_AGENT
        if kwargs.get('timeout') is None:
            kwargs['timeout'] = HTTP_TIMEOUT
        return super().send(request, **kwargs)


class CurrentSongHandler(FileSystemEventHandler):
    """moOde rewrites currentsong.txt in place (truncate + write) when /tmp
    is tmpfs, its default, and by rename from /tmp otherwise. Close-after-
    write and creation are the only moments the file is complete."""

    EVENTS = [FileClosedEvent, FileCreatedEvent, FileMovedEvent]

    def __init__(self, path: Path, scrobbler: Scrobbler, log: Logger):
        self.path = path
        self.scrobbler = scrobbler
        self.log = log

    def on_any_event(self, event: FileSystemEvent) -> None:
        target = os.fsdecode(event.dest_path or event.src_path)
        if os.path.realpath(target) == os.path.realpath(self.path):
            self.refresh()

    def refresh(self) -> None:
        try:
            song = read(self.path)
        except (OSError, UnicodeDecodeError) as e:
            self.log.debug(f"Read err: {e}")
            return
        self.scrobbler.update(song)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='ListenBrainz moOde Scrobbler')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run pipeline without submitting to ListenBrainz')
    parser.add_argument('--version', action='version', version=f'lbms {__version__}')
    return parser.parse_args()


def connect(token: str) -> ListenBrainz:
    lb_client.adapter = Transport(max_retries=lb_client.retry_strategy)
    client = ListenBrainz()
    client.set_auth_token(token, check_validity=False)
    return client


def validate(client: ListenBrainz, token: str, log: Logger, invalid: Event) -> None:
    """Off the startup path: an unreachable API costs minutes of retries,
    and tracks played meanwhile must still be seen (and cached)."""
    log.wait("Token validating")
    try:
        client.set_auth_token(token)
        log.ok("Token valid")
    except InvalidAuthTokenException:
        log.error("Token invalid: check LISTENBRAINZ_TOKEN in .env")
        invalid.set()
    except Exception as e:
        log.warning(f"Token unchecked, offline: {describe(e)}")


def main() -> int:
    args = parse_args()
    print(f"\nLISTENBRAINZ-MOODE-SCROBBLER v{__version__}\n")

    load_dotenv(SRC.parent / '.env')
    try:
        settings = json.loads((SRC / 'settings.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        print(f"Config err: {e}")
        return 1

    log = Logger(settings)
    if not (token := os.getenv('LISTENBRAINZ_TOKEN')):
        log.error("Token not found: LISTENBRAINZ_TOKEN in .env")
        return 1
    log.add_redaction(token)
    if args.dry_run:
        log.wait("Dry run")

    received: list[int] = []
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda signum, _frame: received.append(signum))

    client = connect(token)
    invalid = Event()
    Thread(target=validate, args=(client, token, log, invalid), daemon=True).start()

    cache = None
    if settings['features']['enable_cache']:
        cache = ListenCache(SRC / 'cache' / settings['cache_file'], log)
    scrobbler = Scrobbler(settings, client, cache, log, dry_run=args.dry_run)

    path = Path(settings['currentsong_file'])
    handler = CurrentSongHandler(path, scrobbler, log)
    observer = Observer()
    try:
        observer.schedule(handler, str(path.parent), recursive=False, event_filter=handler.EVENTS)
        observer.start()
    except OSError as e:
        log.error(f"Watch err: {path.parent}: {e}")
        return 1

    log.info(f"Watching: {path}")
    handler.refresh()
    Thread(target=scrobbler.run_cache, args=(CACHE_INTERVAL,), daemon=True).start()

    try:
        while observer.is_alive() and not received and not invalid.is_set():
            observer.join(timeout=1)
    finally:
        observer.stop()
        observer.join()
        scrobbler.shutdown()

    if received:
        log.info(f"Signal {received[0]}: shutdown")
        return 0
    if not invalid.is_set():
        log.error("Watcher lost, exit")
    return 1


if __name__ == "__main__":
    sys.exit(main())
