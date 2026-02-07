#!/usr/bin/env python3
"""Thread-safe logger with configurable levels, format, and timestamp support."""

import logging
from datetime import datetime
from threading import Lock


class Logger:
    """Thread-safe logger with custom levels (WAIT, OK) beyond standard logging."""

    LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "WAIT": logging.INFO + 1,
        "OK": logging.INFO + 2
    }

    def __init__(self, settings=None):
        self.enabled = True
        self.level = "INFO"
        self.format = "[{level}] {message}"
        self.timestamp = False
        self._lock = Lock()

        if settings and 'logging' in settings:
            logging_settings = settings.get('logging', {})
            self.enabled = logging_settings.get('enable', True)
            self.level = logging_settings.get('level', 'INFO').upper()
            self.format = logging_settings.get('format', '[{level}] {message}')
            self.timestamp = logging_settings.get('timestamp', False)

    def _log(self, level, message):
        if not self.enabled or self.LEVELS.get(level, 0) < self.LEVELS.get(self.level, 0):
            return

        with self._lock:
            try:
                parts = []

                if self.timestamp:
                    parts.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])

                output = self.format.format(level=level, message=message)
                parts.append(output)

                print(" ".join(parts), flush=True)
            except Exception as e:
                print(f"[{level}] {message} (Format error: {e})", flush=True)

    def debug(self, message): self._log("DEBUG", message)
    def info(self, message): self._log("INFO", message)
    def wait(self, message): self._log("WAIT", message)
    def ok(self, message): self._log("OK", message)
    def warning(self, message): self._log("WARNING", message)
    def error(self, message): self._log("ERROR", message)

    def print(self, message):
        print(message)
