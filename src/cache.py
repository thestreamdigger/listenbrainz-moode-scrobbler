import json
import os
import tempfile
import time
from collections import deque
from pathlib import Path
from threading import Lock

from liblistenbrainz import Listen, ListenBrainz
from liblistenbrainz.errors import ListenBrainzAPIException, InvalidSubmitListensPayloadException

from logger import Logger

MAX_CACHE_SIZE = 1000
BATCH_SIZE = 50


def rejected(error: Exception) -> bool:
    """True when retrying cannot help: the payload itself was refused.
    Everything else (network, 5xx, 429, revoked token) is transient."""
    if isinstance(error, ListenBrainzAPIException):
        return error.status_code == 400
    return isinstance(error, (TypeError, InvalidSubmitListensPayloadException))


def describe(error: Exception) -> str:
    if isinstance(error, ListenBrainzAPIException):
        return f"HTTP {error.status_code}" + (f": {error.message}" if error.message else "")
    return repr(error)


def submit(client: ListenBrainz, listens: list[dict]) -> None:
    batch = [Listen(**d) for d in listens]
    if len(batch) == 1:
        client.submit_single_listen(batch[0])
    else:
        client.submit_multiple_listens(batch)


class ListenCache:
    def __init__(self, path: Path, log: Logger):
        self.path = path
        self.log = log
        self._lock = Lock()
        self._queue: deque[dict] = deque(maxlen=MAX_CACHE_SIZE)
        self._load()

    def __len__(self) -> int:
        with self._lock:
            return len(self._queue)

    def add(self, listen: dict) -> None:
        with self._lock:
            self._queue.append(listen)
            self._save()

    def flush(self, client: ListenBrainz) -> bool:
        """Submit everything pending, oldest first. False on first transient failure."""
        while True:
            with self._lock:
                batch = [self._queue.popleft() for _ in range(min(BATCH_SIZE, len(self._queue)))]
            if not batch:
                return True
            done = self._submit(client, batch)
            with self._lock:
                self._queue.extendleft(reversed(batch[done:]))
                self._save()
            if done < len(batch):
                return False

    def save(self) -> None:
        with self._lock:
            self._save()

    def _submit(self, client: ListenBrainz, batch: list[dict]) -> int:
        """Listens consumed from the head of batch: sent, or dropped as rejected."""
        try:
            submit(client, batch)
            return len(batch)
        except Exception as e:
            if not rejected(e):
                self.log.warning(f"Cache submit err: {describe(e)}")
                return 0
            if len(batch) == 1:
                self.log.error(f"Cache drop, rejected: {batch[0].get('track_name')} ({describe(e)})")
                return 1
        for done, listen in enumerate(batch):
            if not self._submit(client, [listen]):
                return done
        return len(batch)

    def _load(self) -> None:
        with self._lock:
            try:
                if self.path.exists() and (content := self.path.read_text().strip()):
                    self._queue.extend(json.loads(content))
                    return
            except (OSError, ValueError) as e:
                self.log.error(f"Cache corrupted: {e}")
                backup = self.path.with_name(f"{self.path.name}.corrupt.{int(time.time())}")
                try:
                    self.path.rename(backup)
                    self.log.warning(f"Cache backup: {backup}")
                except OSError as backup_err:
                    self.log.error(f"Cache backup failed: {backup_err}")
            self._save()

    def _save(self) -> None:
        """Atomic write: temp file, fsync, replace, fsync dir. Caller holds the lock."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".lbms_cache_", dir=self.path.parent)
            try:
                with os.fdopen(fd, 'w') as f:
                    json.dump(list(self._queue), f)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, self.path)
                dir_fd = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
        except OSError as e:
            self.log.error(f"Cache save failed: {e}")
