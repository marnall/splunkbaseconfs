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
# File: app/config.py
#
# Author: alexeiyur AT g m 4 i l . c 0 m
# Licensed under the MIT License (https://mit-license.org/)

import copy
import json
import logging
import optparse
import os
import re
import sys
import time
from contextlib import contextmanager
from datetime import datetime

import app
from app.env import UpdateLoggingPath, confpath, datapath


def versionTuple(v):
    return tuple(s.zfill(8) for s in v.split("."))


# OBSOLETE Need to load json properly in PY2
def byteify(inp):
    if isinstance(inp, dict):
        # NOTE No dict comprehension in 2.6 (the version on QRadar box as of 7.3 and earlier)
        # return dict([(byteify(key), byteify(value)) for key, value in iteritems(inp)])
        return {byteify(key): byteify(value) for key, value in inp.items()}
    elif isinstance(inp, list):
        return [byteify(element) for element in inp]
    # elif isinstance(inp, string_types):
    #     if PY2:
    #         return inp.encode('utf-8')
    #     else:
    #         return inp
    else:
        return inp


# Convert the object to dict for saving to json
def to_dict(obj):
    # Some platforms like Demisto use custom Python build which ends up putting any custom class into 'builtins'
    # HACK Work around the above limitation by a naive check for simple type names ever used in the config data (json)
    #      This assumes __class__ field holds "<class 'name'>". Assume the following builtin types:
    #      bool, int, float, str, list, dict
    # mod = obj.__class__.__module__
    # if mod not in ['builtins', '__builtin__']:
    tname = str(obj.__class__)[8:-2]
    if tname not in ["bool", "int", "float", "str", "list", "dict"]:
        # TODO Check for methods and classes to exclude them and get rid of the underscore in their names
        # NOTE No dict comprehension in 2.6 (the version on QRadar box as of 7.3 and earlier)
        # return dict([(key, to_dict(getattr(obj, key)))
        #             for key in dir(obj) if not key.startswith('_') and 'status' not in key])
        return {key: to_dict(getattr(obj, key)) for key in dir(obj) if not key.startswith("_") and "status" not in key}

    if type(obj).__name__ == "list":
        return [to_dict(el) for el in obj]
    else:
        return obj


# Thread operation status to report to UI
class Status:
    def __init__(self):
        self.lastRes = None
        self.lastMsg = "In progress"
        self.lastLog = "{}"
        self.lastTime = datetime.utcnow()
        self.cntSuccess = 0
        self.cntError = 0
        self.updateCount = 0

    def ok(self):
        return self.lastMsg == "ok"


# Need this hack because this ancient Jinja 2.7.3 version used by QRadar
# doesn't have the simple 'in' built-in test! Not even 'equalto'!!
class Feature:
    def __init__(self, name):
        setattr(self, name, True)

    def __getitem__(self, item):
        return getattr(self, item)


@contextmanager
def tempfile(filepath, mode, suffix=""):
    undersplunk = False
    if undersplunk:
        # For Splunk, the run environment is managed by Splunk so there is no need in temp files to sync writes
        # The cloud certification reports 'file operation outside of the app directory' etc. but this is mistaken
        # To be on the safe side, have the temp file code disabled since it's not needed under Splunk anyways
        yield filepath
        return

    import tempfile as tmp

    ddir = os.path.dirname(filepath)
    tf = tmp.NamedTemporaryFile(dir=ddir, mode=mode, delete=False, suffix=suffix)
    tf.file.close()  # type: ignore[attr-defined]
    yield tf.name

    try:
        os.remove(tf.name)
    except OSError as e:
        if e.errno != 2:
            raise e


@contextmanager
def open_atomic(filepath, mode, **kwargs):
    with tempfile(filepath, mode=mode) as tmppath:
        with open(tmppath, mode=mode, **kwargs) as file:
            yield file
            file.flush()
            os.fsync(file.fileno())
        if tmppath != filepath:
            os.rename(tmppath, filepath)


class Config:
    version = "1.0.12"
    _api_version_min = "1.0.7"
    _api_version_max = "1.1.5"
    _default = None

    _flags = dict(
        logging_level=("-l", "loglevel field, defaults to WARNING, options are: CRITICAL, ERROR, WARNING, INFO, DEBUG"),
        featureset=(
            "-f",
            "featureset (SIEM/SOAR platform name), defaults to unknown with no file i/o available, options are: debug,"
            "bitglass, qradar, splunk, phantom, demisto",
        ),
    )

    def _genOptions(self):
        p = optparse.OptionParser()
        for k, f in self._flags.items():
            p.add_option(
                f[0],
                "--" + (k if k[0] != "_" else k[1:]),
                dest=k,
                # Default password is '' rather than default password object to keep plain comparisons working in general case
                default=getattr(self._default, k) if f[0] not in ["-a", "-k"] else "",
                help=f[1],
            )
        return p

    def _applyOptionValue(self, name, value, current, default, secret):
        if value == current:
            return

        if value == default:
            app.logger.info(f'Ignored override with implicit default of config param "{name}" of:\n{getattr(self, name)!s}')
            return

        app.logger.info(f"Overriding config param {name} with:\n{value!s}")
        if current != default:
            app.logger.info(f'\t- double override of config param "{name}" of:\n{getattr(self, name)!s}')
        if secret is None:
            setattr(self, name, value)
        else:
            secret.secret = value

    def _applyOptionsOnce(self, opts=None):
        # No validation is done on command line options letting it fail wherever..
        # It's not too bad as long as no corrupted data is saved
        # TODO Do validation (borrowing from UI code??).. make sure it's never saved for now
        # HACK Reuse _save method as flag
        if self._save is None:
            return ""
        self._save = None  # type: ignore[assignment]

        if opts is None:
            # Unless need to parse the remaining arguments..
            opts, args = self._genOptions().parse_args()
            if len(args) > 0:
                app.logger.warning(f'Ignored unknown options "{args!s}"')
        else:
            args = ""

        # If something bad happens, the config may be half-set but it's OK since it's never saved
        for k, f in self._flags.items():
            p = getattr(opts, k)
            # HACK Check for patterns in help string to additionally parse into list etc.
            if f[0] == "-f":
                if isinstance(p, str):
                    p = [{p: True}]
            elif ":]" in f[1]:
                if isinstance(p, str):
                    p = p.split(":")
                p.sort()
            elif ", seconds" in f[1]:
                if isinstance(p, str):
                    p = int(p)
            if "password" in f[1] or "token" in f[1]:
                s = getattr(self, k)
                v = getattr(self, k).secret
                d = getattr(self._default, k).secret
            else:
                s = None
                v = getattr(self, k)
                d = getattr(self._default, k)

            self._applyOptionValue(k, p, v, d, s)

        # TODO Only after validation
        self._calculateOptions()  # type: ignore[attr-defined]    # pylint: disable=E1101

        return args

    def _getvars(self):
        return vars(self)

    def _loadFile(self, fname):
        d = {}
        if self._context is not None:
            name = os.path.basename(fname)
            d = (
                (json.loads(self._context[name]) if isinstance(self._context[name], str) else self._context[name])
                if name in self._context
                else {}
            )
        else:
            with open(fname) as f:
                d = json.load(f)

        if d:
            for key, value in d.items():
                setattr(self, key, value)
                # if 'config.json' in fname:
                #     app.config[key] = value

    def _load(self, fname):
        if fname is None:
            return

        errMsg = "Could not load last configuration %s across app sessions: %s"

        try:
            self._loadFile(fname)
        except Exception as ex:
            if confpath:
                # Initial config data is kept in a separate (container) directory
                try:
                    fname = os.path.join(os.path.dirname(fname), confpath, os.path.basename(fname))
                    self._loadFile(fname)
                except Exception as ex:
                    app.logger.info(errMsg % (fname, ex))
            else:
                app.logger.info(errMsg % (fname, ex))

    def _deepcopy(self):
        # Secrets contain the session inside to tie them to the user
        auth_token = self._auth_token  # type: ignore[has-type]    # pylint: disable=E0203
        password = self._password  # type: ignore[has-type]    # pylint: disable=E0203
        proxies_pswd = self._proxies_pswd  # type: ignore[has-type]    # pylint: disable=E0203
        self._auth_token = None
        self._password = None
        self._proxies_pswd = None

        session = self._session  # type: ignore[has-type]
        self._session = None
        cp = copy.deepcopy(self)
        self._session = session

        self._auth_token = auth_token
        self._password = password
        self._proxies_pswd = proxies_pswd
        cp._auth_token = auth_token
        cp._password = password
        cp._proxies_pswd = proxies_pswd
        return cp

    def __init__(self, fname=None, session={}, context=None):
        self._folder = datapath
        self._fname = os.path.join(self._folder, fname) if fname else None
        self._context = context
        self._isDaemon = True

        # Assume there is no file system to read from for unknown platform
        self.featureset = []

        self.logging_level = "WARNING"

        self.updateCount = 0

        # Latest update count when any settings changed. It will be compared to the message update count.
        # When the message update count is at least this, it will be printed in color (vs. in a pop up of
        # 'In progress' status entry, because the message is stale in regards to the most recent settings)
        self.updateCountChanged = 0

        if self._default is None:
            self._default = copy.deepcopy(self)

        self._load(self._fname)

        # Read/override common config properties, read-only - never saved
        # TODO Optimize by reading only once for all config objects
        self._load(os.path.join(self._folder, "config.json"))

        if versionTuple(self.version) >= versionTuple("1.0.13"):
            self.featureset += [{"health": True}]

        # NOTE Crashes when gets called before active request available (
        # Copy relevant session data so it's available to any page/form
        # self._session = {}
        # sessionKeys = ['logged_in']
        # for k in sessionKeys:
        #     if k in session:
        #         self._session[k] = session[k]
        self._session = session

    @contextmanager
    def _lock(conf, condition, notify=True):  # pylint: disable=E0213 # TODO Switch conf to self
        if condition is not None:
            condition.acquire()
        yield conf
        if notify:
            conf.updateCount = conf.updateCount + 1
        if condition is not None:
            if notify:
                condition.notify()
            condition.release()
        elif notify:
            conf.status["updateCount"] = conf.updateCount  # type: ignore[attr-defined]    # pylint: disable=E1101

    def _isEnabled(self, featureName):
        for f in self.featureset:
            if hasattr(f, "__dict__"):
                if featureName in f.__dict__:
                    return True
            else:
                if featureName in f:
                    return True
        return False

    def _isNoConfigStore(self):
        return self.featureset == []

    def _isForeignConfigStore(self):
        return self._isNoConfigStore() or not (self._isEnabled("qradar") or self._isEnabled("bitglass"))

    def _save(self):  # pylint: disable=E0202
        if self._fname is None:
            # Nothing to save (just config.json - read-only)
            return

        try:
            d = to_dict(self)
            # Exclude base properties (assumed read-only)
            if type(self).__name__ != "Config":
                vs = vars(Config())
                for el in list(d.keys()):
                    if el in vs:
                        del d[el]
            # Exclude properties with default values
            for el in list(d.keys()):
                if hasattr(self._default, el) and d[el] == getattr(self._default, el):
                    del d[el]
            if len(d) > 0:
                if self._context is not None:
                    name = os.path.basename(self._fname)
                    self._context[name] = json.dumps(d, sort_keys=False)
                    self._context.save()
                else:
                    # Protect against writing from multiple sessions
                    with open_atomic(self._fname, "w") as f:
                        json.dump(d, f, indent=2, sort_keys=False)
        except Exception as ex:
            app.logger.warning(f"Could not save last configuration {self._fname} across app sessions: {ex}")

    def _waitForStatus(self, secs):
        interval = 0.5
        for _ in range(int(secs / interval)):
            if self.status["updateCount"] >= self.updateCount:  # type: ignore[attr-defined]    # pylint: disable=E1101
                break
            time.sleep(interval)

    def _updateAndWaitForStatus(self, condition, rform):
        return False

    def _matchHost(self, h):
        # '^(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-9]|2\d|3[0-1])'
        #   '(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5]))'
        #   '{2}(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))\.|(?:(?:[a-z_-][a-z0-9_-]{0,62})?[a-z0-9]\.)+(?:[a-z]{2,}\.?)?)$'
        return re.match(
            r"^(?:"  # FIXED Added ^
            # IP address exclusion
            # private & local networks
            # FIXED: Commented out to allow private and local
            #   r'(?!(?:10|127)(?:\.\d{1,3}){3})'
            #   r'(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})'
            #   r'(?!172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})'
            # IP address dotted notation octets
            # excludes loopback network 0.0.0.0
            # excludes reserved space >= 224.0.0.0
            # excludes network & broadcast addresses
            # (first & last IP address of each class)
            # TODO Figure out if need keeping any of those excluded
            r"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
            r"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}"
            r"(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))"
            r"\.|"  # FIXED original u"|", this is a trick to match 'localhost' by appending '.'
            # host & domain names, may end with dot
            r"(?:"
            r"(?:"
            # r'[a-z0-9\u00a1-\uffff]'
            # r'[a-z0-9\u00a1-\uffff_-]{0,62}'
            # FIXED original u"[a-z0-9_-]", allowing digits in the first position
            # discards all ip matching before (like disallowing 127.x.x.x)
            r"[a-z_-]"
            r"[a-z0-9_-]{0,62}"
            r")?"
            # r'[a-z0-9\u00a1-\uffff]\.'
            r"[a-z0-9]\."
            r")+"
            # TLD identifier name, may end with dot
            # r'(?:[a-z\u00a1-\uffff]{2,}\.?)"
            r"(?:[a-z]{2,}\.?)?"  # FIXED Made it optional by appending '?' to support 'localhost'
            r")$",  # FIXED Added $
            h + ".",
            re.I,
        )  # FIXED Append '.'


startConf = Config()


def setPythonLoggingLevel(logger, conf=startConf):
    """Set/override python logging level from the config"""

    if startConf._isNoConfigStore():
        return 0

    numeric_level = getattr(logging, conf.logging_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {conf.logging_level}")

    logger.setLevel(numeric_level)
    for hdlr in logger.handlers:
        hdlr.setLevel(numeric_level)

    # Should have it as warning so it's visible by default but.. don't want to overflow the log
    # when it's run periodically as a command..
    logger.info(f"~~~ LOGGING ENABLED AT LEVEL: {conf.logging_level} ~~~")
    return numeric_level


def setPythonLogging(logger=None, defaultlogfolder=startConf._folder):
    """Set python logging options for a script (vs. a Flask app)"""

    if startConf._isNoConfigStore():
        # TODO Use similar solution for Phantom (currently, all standard python logging is ignored as if sent to null device)
        # Currently, this crude solution (without levels) is for Demisto
        return app.Logger(nop=LOG)

    filename = UpdateLoggingPath(defaultlogfolder)

    if startConf._isEnabled("qradar"):
        # Create logger wrapping qpylib API + Flask
        from app.flaskinit import log, set_log_level  # pylint: disable=E0401

        return app.Logger(startConf, log, set_log_level)

    # Grab the logger object
    addStderr = False
    if logger is None:
        # Create one instead of borrowing the Flask one. Create stderr handler instead of the Flask one
        addStderr = True
        logger = logging.getLogger("com.bitglass.lss")

    # This enables werkzeug logging
    # logging.basicConfig(filename=, level=)

    # Set default logging level from config
    numeric_level = setPythonLoggingLevel(logger)

    # Show thread and full path with INFO and up
    fmt = """%(asctime)s [%(filename)s:%(lineno)d] [%(levelname)s]\n\t%(message)s"""
    if numeric_level <= logging.INFO:
        fmt = """%(asctime)s,%(msecs)d [%(pathname)s:%(lineno)d] [%(thread)d] [%(levelname)s]\n\t%(message)s"""

    # Log to bitglass.log file
    fh = logging.FileHandler(filename=filename)
    fh.setLevel(numeric_level)

    formatter = logging.Formatter(fmt, "%Y-%m-%d %H:%M:%S")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if addStderr:
        # Log to STDERROR as well since it's run as a cli script
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(numeric_level)

        # Stderr may be loaded into SIEMs like Splunk etc. so careful changing the format
        formatterStderr = formatter
        sh.setFormatter(formatterStderr)
        logger.addHandler(sh)
        logger.info("~~~ Running in CLI mode (Python logging set) ~~~")

    return logger
