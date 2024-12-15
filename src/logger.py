#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ListenBrainz moOde Scrobbler - Logger Module
# Copyright (C) 2023 StreamDigger
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
        
        if settings:
            logging_settings = settings.get('logging', {})
            self.enabled = logging_settings.get('enable', True)
            self.level = logging_settings.get('level', 'INFO').upper()
            self.format = logging_settings.get('format', '[{level}] {message}')

    def _log(self, level, message):
        if not self.enabled or self.LEVELS[self.level] > self.LEVELS[level]:
            return
            
        print(self.format.format(
            level=level,
            message=message
        ))

    def debug(self, message): self._log("DEBUG", message)
    def info(self, message): self._log("INFO", message)
    def wait(self, message): self._log("WAIT", message)
    def ok(self, message): self._log("OK", message)
    def warning(self, message): self._log("WARNING", message)
    def error(self, message): self._log("ERROR", message) 