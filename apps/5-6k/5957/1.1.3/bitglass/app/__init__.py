# Copyright (c) 2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# File: app/__init__.py
#
# Author: alexeiyur AT g m 4 i l . c 0 m
# Licensed under the MIT License (https://mit-license.org/)
__author__ = "alexeiyur"


class Logger:
    """For redirecting logging output to proprietory platform APIs (such as QRadar).
    Default ctor is equivalent to logging not defined as the case is when on some platforms
    one needs to know the data path from the config first before can initialize logging.
    This allows for using app.logger.xyz() across the app in a portable way across platforms.
    By default the standard python 'logging' module is used whenever possible.
    """

    def debug(self, msg):  # pylint: disable=E0202
        self.log(msg, level="DEBUG")

    def info(self, msg):  # pylint: disable=E0202
        self.log(msg, level="INFO")

    def warning(self, msg):  # pylint: disable=E0202
        self.log(msg, level="WARNING")

    def error(self, msg):  # pylint: disable=E0202
        self.log(msg, level="ERROR")

    def nop(self, msg):  # pylint: disable=E0202
        pass

    def __bool__(self):
        return bool(self.conf)

    # TODO Remove Python 2 crutch
    def __nonzero__(self):
        return self.__bool__()

    def __init__(self, conf=None, log=None, set_log_level=None, nop=None):
        self.conf = conf
        self.log = log
        if nop:
            self.nop = nop  # type: ignore[assignment]
        if conf and log and set_log_level:
            if "error" in conf.logging_level.lower():
                set_log_level("ERROR")
                self.debug = self.nop  # type: ignore[assignment]
                self.info = self.nop  # type: ignore[assignment]
                self.warning = self.nop  # type: ignore[assignment]
            elif "warn" in conf.logging_level.lower():
                set_log_level("WARNING")
                self.debug = self.nop  # type: ignore[assignment]
                self.info = self.nop  # type: ignore[assignment]
            elif "info" in conf.logging_level.lower():
                set_log_level("INFO")
                self.info = self.nop  # type: ignore[assignment]
        else:
            self.debug = self.nop  # type: ignore[assignment]
            self.info = self.nop  # type: ignore[assignment]
            self.warning = self.nop  # type: ignore[assignment]
            self.error = self.nop  # type: ignore[assignment]


# Can't initialize here b/c it's data path dependent (different for different platforms)
logger = Logger()


# Uncomment for the merged module support
# class App:
#    Logger = Logger
#
#     def __init__(self, logger):
#         self.logger = demisto
#
#
# app = App(logger)


# Skip this part for the merged module support
try:
    # Export for gunicorn (and QRadar, required by the upgrade scenario to be app:app)
    from app.flaskinit import application as app

    # UI initialized successfully
    pass

# Not ImportError, to support arbitrary failing of cli integrations from the flat package, just in case
except Exception as e:  # nosec
    # UI error
    pass  # nosec
