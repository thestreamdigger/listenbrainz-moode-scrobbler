#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ListenBrainz moOde Scrobbler - Logger Module v0.1.0
# Copyright (C) 2024 StreamDigger
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import logging
from threading import Lock
import threading
from datetime import datetime

class Logger:
    LEVELS = {
        "DEBUG": logging.DEBUG,      # 10
        "INFO": logging.INFO,        # 20
        "WARNING": logging.WARNING,  # 30
        "ERROR": logging.ERROR,      # 40
        "CRITICAL": logging.CRITICAL,# 50
        "WAIT": logging.INFO + 1,    # 21
        "OK": logging.INFO + 2       # 22
    }

    def __init__(self, settings=None):
        self.enabled = True
        self.level = "INFO"
        self.format = "[{level}] {message}"
        self.timestamp = False
        self._lock = Lock()
        
        if settings:
            logging_settings = settings.get('logging', {})
            self.enabled = logging_settings.get('enable', True)
            self.level = logging_settings.get('level', 'INFO').upper()
            self.format = logging_settings.get('format', '[{level}] {message}')
            self.timestamp = logging_settings.get('timestamp', False)

    def _log(self, level, message):
        if not self.enabled or self.LEVELS[level] < self.LEVELS[self.level]:
            return
            
        with self._lock:
            try:
                parts = []
                
                if self.timestamp:
                    parts.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
                    
                output = self.format.format(
                    level=level,
                    message=message
                )
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