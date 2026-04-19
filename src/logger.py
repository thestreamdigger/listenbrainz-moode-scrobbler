#!/usr/bin/env python3
"""Thread-safe logger with configurable levels, format, and timestamp support."""

import logging
from datetime import datetime
from threading import Lock


class Logger:
    """Thread-safe logger with custom levels (WAIT, OK) and redaction support."""

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
        self._redactions = []

        if settings and 'logging' in settings:
            logging_settings = settings.get('logging', {})
            self.enabled = logging_settings.get('enable', True)
            self.level = logging_settings.get('level', 'INFO').upper()
            self.format = logging_settings.get('format', '[{level}] {message}')
            self.timestamp = logging_settings.get('timestamp', False)

    def add_redaction(self, text, replacement="****"):
        if not text:
            return
        with self._lock:
            if (text, replacement) not in self._redactions:
                self._redactions.append((text, replacement))

    def _log(self, level, message):
        if not self.enabled or self.LEVELS.get(level, 0) < self.LEVELS.get(self.level, 0):
            return

        with self._lock:
            try:
                safe_message = message
                for text, replacement in self._redactions:
                    safe_message = str(safe_message).replace(text, replacement)

                parts = []

                if self.timestamp:
                    parts.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])

                output = self.format.format(level=level, message=safe_message)
                parts.append(output)

                print(" ".join(parts), flush=True)
            except Exception as e:
                print(f"[{level}] {message} (Format err: {e})", flush=True)

    def debug(self, message): self._log("DEBUG", message)
    def info(self, message): self._log("INFO", message)
    def wait(self, message): self._log("WAIT", message)
    def ok(self, message): self._log("OK", message)
    def warning(self, message): self._log("WARNING", message)
    def error(self, message): self._log("ERROR", message)
