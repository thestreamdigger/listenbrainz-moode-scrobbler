import logging
from datetime import datetime
from threading import RLock


class Logger:
    LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "WAIT": logging.INFO + 1,
        "OK": logging.INFO + 2
    }

    def __init__(self, settings: dict | None = None):
        config = (settings or {}).get('logging', {})
        self.enabled = config.get('enable', True)
        self.level = config.get('level', 'INFO').upper()
        self.format = config.get('format', '[{level}] {message}')
        self.timestamp = config.get('timestamp', False)
        self._lock = RLock()
        self._redactions: list[tuple[str, str]] = []

    def add_redaction(self, text: str, replacement: str = "****") -> None:
        if not text:
            return
        with self._lock:
            if (text, replacement) not in self._redactions:
                self._redactions.append((text, replacement))

    def _log(self, level: str, message: object) -> None:
        if not self.enabled or self.LEVELS.get(level, 0) < self.LEVELS.get(self.level, 0):
            return

        with self._lock:
            text = str(message)
            for secret, replacement in self._redactions:
                text = text.replace(secret, replacement)
            try:
                line = self.format.format(level=level, message=text)
            except (KeyError, IndexError, ValueError) as e:
                line = f"[{level}] {text} (Format err: {e})"
            if self.timestamp:
                line = f"{datetime.now():%Y-%m-%d %H:%M:%S.%f}"[:-3] + f" {line}"
            print(line, flush=True)

    def debug(self, message: object) -> None: self._log("DEBUG", message)
    def info(self, message: object) -> None: self._log("INFO", message)
    def wait(self, message: object) -> None: self._log("WAIT", message)
    def ok(self, message: object) -> None: self._log("OK", message)
    def warning(self, message: object) -> None: self._log("WARNING", message)
    def error(self, message: object) -> None: self._log("ERROR", message)
