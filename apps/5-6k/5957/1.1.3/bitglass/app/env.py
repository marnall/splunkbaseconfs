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
# File: app/env.py
#
# Author: alexeiyur AT g m 4 i l . c 0 m
# Licensed under the MIT License (https://mit-license.org/)

import os


# Use os.path.abspath() if ever wish running standalone on Windows
datapath = os.path.join(os.sep, "store", "")
loggingpath = os.path.join(datapath, "app.log")

# Additional relative path to look for for the initial configs (usually in the container)
confpath = None


def isOptDir(name):
    """Need this to support multiple platform installations on the same instance"""
    # TODO Using __file__ would be invalid for pypi lib
    # Move all __file__ use outside of the shared lib
    return os.path.join(os.sep, "opt", name, "") in __file__


def initDataPath():
    global datapath
    global confpath

    # NOTE To the curious minds wondering about the purpose of the if/all()/any()/lambda constructs used throughout the code:
    #      It's used to satisfy conflicting flake8 requirements among different platforms while keeping the LAZY evaluation.
    #      Specifically, the W504 warning and its ilk. IMO these warnings are excercises in hair splitting and pure evil, they
    #      should have never been put in the warning category to begin with (de facto the error category for the purpose of the
    #      mandatory certification lint scans). BTW, it wouldn't be so bad if not for the confusion between flake8's 'ignore' and
    #      'extend-ignore' statements, the former being misused by some environments thus inadvertently activating the
    #      conflicting options.

    # For Splunk - read-only forward.json (just for the extra options) as the Save button saves to appsetup.conf
    # Also, the local/ folder will be empty (the contents are moved over to default/ by the addon builder)
    if all(a() for a in [lambda: "SPLUNK_HOME" in os.environ, lambda: isOptDir("splunk")]):
        datapath = os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", "bitglass", "default", "")

    elif all(
        a()
        for a in [
            lambda: os.path.isdir(
                os.path.join(os.sep, "opt", "phantom", "local_data", "app_states", "8119e222-818e-42f5-a210-1c7c9d337e81", "")
            ),
            lambda: isOptDir("phantom"),
        ]
    ):
        # TODO Fix reading config.json, right now all defaults are loaded since it's sought after in the logging folder.
        #      See UpdateDataPath() that sets it
        # datapath = # Can't use __file__ b/c of it being a pypi lib
        confpath = "config"

    # NOTE: To support upgrades properly, check the newest stuff first!

    # New QRadar >= 7.4 app
    elif all(a() for a in [lambda: os.path.isdir(os.path.join(os.sep, "opt", "app-root", "")), lambda: isOptDir("app-root")]):
        datapath = os.path.join(os.sep, "opt", "app-root", "store", "")
        confpath = "../container/conf"

        # NOTE Not needed as we have the app object exported from __init__.py as well (any object name will do in fact)
        # Have to Set up magic environment variables to keep it backwards-compatible with QRadar 7.3.x
        # os.environ['FLASK_APP'] = 'app.flaskinit:application'
        if "FLASK_APP" not in os.environ:
            os.environ["FLASK_APP"] = "app"

        if "QRADAR_CONSOLE_IP" not in os.environ:
            # To prevent an exception (new QRadar behavior) when the var is not set in dev container
            os.environ["QRADAR_CONSOLE_IP"] = "127.0.0.1"

    # Standalone Bitglass app
    elif all(a() for a in [lambda: os.path.isdir(os.path.join(os.sep, "opt", "bitglass", "store", "")), lambda: isOptDir("bitglass")]):
        datapath = os.path.join(os.sep, "opt", "bitglass", "store", "")


def UpdateDataPath(newpath):
    """The app calls this to override for the paths that include container uuids"""
    global datapath

    res = datapath != newpath
    datapath = newpath
    return res


def UpdateLoggingPath(defaultlogfolder=None):
    global loggingpath

    if all(a() for a in [lambda: "SPLUNK_HOME" in os.environ, lambda: isOptDir("splunk")]):
        loggingpath = os.path.join(os.environ["SPLUNK_HOME"], "var", "log", "splunk", "bitglass.log")
    # Can't use PHANTOM_LOG_DIR (not defined), /opt/phantom/var/log/phantom/apps is missing on the OVA too
    # (the latter uses /opt/phantom...) and would have to create bitglass/ directory in either anyways..
    # TODO Should probably read 'appid' from bitglass.json
    elif all(
        a()
        for a in [
            lambda: os.path.isdir(
                os.path.join(os.sep, "opt", "phantom", "local_data", "app_states", "8119e222-818e-42f5-a210-1c7c9d337e81", "")
            ),
            lambda: isOptDir("phantom"),
        ]
    ):
        loggingpath = os.path.join(os.sep, "opt", "phantom", "local_data", "app_states", "8119e222-818e-42f5-a210-1c7c9d337e81", "bitglass.log")
    # Deployed LSS instance
    elif all(a() for a in [lambda: os.path.isdir(os.path.join(os.sep, "var", "log", "bitglass", "")), lambda: isOptDir("bitglass")]):
        loggingpath = os.path.join(os.sep, "var", "log", "bitglass", "app.log")
    # New QRadar >= 7.4 app
    elif all(a() for a in [lambda: os.path.isdir(os.path.join(os.sep, "opt", "app-root", "")), lambda: isOptDir("app-root")]):
        loggingpath = os.path.join(os.sep, "opt", "app-root", "store", "log", "app.log")
    else:
        if defaultlogfolder:
            loggingpath = os.path.join(defaultlogfolder, "log", "app.log")
        else:
            loggingpath = os.path.join(datapath, "app.log")

    # Phantom logs to /var/log/phantom/spawn.log
    # Can detect the version with 'cat /opt/phantom/etc/settings.json | grep phantom_version'
    return loggingpath


try:
    # Some platforms like Demisto run code from a string where __file__ is not defined (and file i/o is not defined either)
    initDataPath()
    UpdateLoggingPath()
except Exception:  # nosec
    # May or may not get here for such platforms
    pass  # nosec
