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
# File: app/configForward.py
#
# Author: alexeiyur AT g m 4 i l . c 0 m
# Licensed under the MIT License (https://mit-license.org/)

import re

import app
from app.config import Config, Status

# This is the inconvenience to keep the static security scanners happy (could have used import * instead)
from app.consts import (
    GC_LOGTYPE_ACCESS,
    GC_LOGTYPE_ADMIN,
    GC_LOGTYPE_CLOUDAUDIT,
    GC_LOGTYPE_CLOUDSUMMARY,
    GC_LOGTYPE_HEALTHAPI,
    GC_LOGTYPE_HEALTHPROXY,
    GC_LOGTYPE_HEALTHSYSTEM,
    GC_LOGTYPE_SWGWEB,
    GC_LOGTYPE_SWGWEBDLP,
    GC_RESETTIME,
)
from app.secret import MULTI_PSWD_SEP_CHAR, Password


try:
    from flask import session
except ImportError:
    session = {}


sources = [
    ("invalid.xyz", "Bearer", ""),
    ("invalid.xyz", "Basic", ""),
]

log_types = [
    GC_LOGTYPE_CLOUDAUDIT,
    GC_LOGTYPE_ACCESS,
    GC_LOGTYPE_ADMIN,
    GC_LOGTYPE_CLOUDSUMMARY,
    GC_LOGTYPE_SWGWEB,
    GC_LOGTYPE_SWGWEBDLP,
    GC_LOGTYPE_HEALTHPROXY,
    GC_LOGTYPE_HEALTHAPI,
    GC_LOGTYPE_HEALTHSYSTEM,
]


class ConfigForward(Config):
    #
    # Old flags delta for reference
    #

    # p = optparse.OptionParser("usage: %prog [options]")

    # Not implemented yet.. why need it?
    # p.add_option(
    #     "-o",
    #     "--host", dest="host", default='localhost', help='hostname or ip address for splunk host, defaults to localhost')
    # p.add_option(
    #     "-p",
    #     "--port", dest="port", type='int', default=9200, help='TCP or UDP port for splunk host, defaults to 9200')

    # ??
    # p.add_option(
    #     "-i",
    #     "--index", dest="index", default=None, help='Json file with index details, defaults to None')

    # fixed
    # p.add_option(
    #     "-v",
    #     "--version", dest="version", default='1.1.0', help='api version field, defaults to 1.1.0')
    # only json
    # p.add_option(
    #     "-d",
    #     "--dataformat", dest="dataformat", default='json', help='requested api dataformat, json or csv, defaults to json')
    # -r :port does it
    # p.add_option(
    #     "-P",
    #     "--Port", dest="Port", type='int', default=0, help='TCP or UDP port for syslog daemonized listening, defaults to 0"
    #       " - skip and exit'")
    # not used, no buffering
    # p.add_option(
    #     "-e",
    #     "--eps", dest="eps", type='int', default=500, help='events per second, if set to a value larger then 0 throttling"
    #       " will be applied, defaults to 500'")

    # Command line flags to override properties
    Config._flags.update(
        dict(
            customer=("-c", "customer field, defaults to Bitglass"),
            api_url=("-r", 'url for portal access or syslog ":port" to listen on, required'),
            sink_url=("-n", 'send output messages over url, TCP socket, UDP syslog (default "0.0.0.0:514") or stdout'),
            log_types=(
                "-t",
                'logtype field "[access:][admin:][cloudaudit:][swgweb:][swgwebdlp:][healthproxy:][healthapi:][healthsystem:]cloudsummary"',
            ),
            _username=("-u", "user name for portal access"),
            _password=("-k", "password for portal access"),
            # extra
            _auth_token=("-a", "OAuth 2 token for portal access"),
            log_interval=("-d", "log interval, seconds"),
            log_initial=("-i", "log initial period, seconds"),
            # - TODO proxies, reset_time
        )
    )

    def __init__(self, context=None):
        self.status = {"updateCount": 0, "last": Status()}
        for log_type in log_types:
            self.status[log_type] = Status()

        # Can't keep it here b/c of deepcopying
        # self._condition = condition

        # Load some (useful) hard-coded defaults
        source = 0
        self._auth_type = False
        self._use_proxy = False
        self.host = sources[source][0]
        self.api_ver = self._api_version_max
        self.auth_type = sources[source][1]
        self._auth_token = Password("auth_token")
        self._username = ""
        self._password = Password("password")
        self._proxies_pswd = Password("proxies_pswd")
        #
        self.log_types = [log_types[0]]
        self.log_interval = 900
        # self.api_url        = 'https://portal.us.%s/api/bitglassapi/logs/' % self.host
        self.api_url = ""
        self.proxies = None
        self.sink_url = "localhost:514"

        h, p = self.sink_url.split(":") if ":" in self.sink_url else (self.sink_url, "514")
        self._syslogDest = (h, int(p))

        # Additional params not in the UI. Don't save for now
        self.log_initial = 30 * 24 * 3600
        self._max_request_rate = 10

        # Last log reset..
        # It's reset automatically back to the default upon use. Never persist (starts with underscore)!
        self._reset_time = ""
        # Empty the contents of lastlog files just short of deleting the files (vs. resetting the 'time' field to preserve
        # the other data for easy troubleshooting)
        self.hardreset = True
        # Used only by x_*.py modules' code where an alternative config store is used without the read-once-reset-to-default
        # functionality like Splunk
        self.reset_fence = ""

        # Additional (optional) settings, not exposed in the UI for now
        self.verify = True
        self.customer = "Bitglass"
        self.useNextPageToken = True

        self.postTimeoutChanged = 30

        # Refresh timeout (0 - no waiting by default unless some settings changed - see the param above)
        self.postTimeoutRefresh = 0

        super().__init__("forward.json", session, context)

        # Clobber unsupported log types by app version to allow for testing new types before releasing officially
        # if False:     # For testing
        if not self._isEnabled("health"):
            for lt in ["healthproxy", "healthapi", "healthsystem"]:
                if lt in self.log_types:
                    self.log_types.remove(lt)

        # Provide session after the defaults have been deep-copied
        self._auth_token = Password("auth_token", session)
        self._password = Password("password", session)
        self._proxies_pswd = Password("proxies_pswd", session)

        # Cut down requests for debugging
        if self._isEnabled("debug"):
            self.log_initial = 7 * 24 * 3600

        # Load secrets (if managing secure storage)
        if all(
            a() for a in [lambda: not self._isEnabled("splunk"), lambda: not self._isEnabled("phantom"), lambda: not self._isEnabled("demisto")]
        ):
            self._auth_token.load(self)
            self._password.load(self)
            self._proxies_pswd.load(self)

        # Sort any lists so can rely on bulk comparison
        self.log_types.sort()

    # From param dict to canonical string to load to UI, assume username never
    # contains \' and no ', ' in either the username or password
    def _printProxies(self, proxies):
        return (
            str(proxies).replace("': ", "'=").replace(", ", "\n").replace("'", "").replace('"', "").replace("{", "").replace("}", "")
            if proxies is not None
            else ""
        )

    # From user multi-string to detailed dict list
    def _parseProxies(self, s):
        proxies = {}  # type: ignore[var-annotated]
        if s == "":
            return proxies

        pxs = s.replace("\r", "").split("\n")
        for p in pxs:
            # Skip all-whitespace lines
            if p.replace(" ", "") == "":
                continue

            proxy = {}
            try:
                # TODO Handle unicode data properly

                # Either = or : assignment, quotes are optional, username, password and port are optional
                #
                # 'nttps=nttps;\\user;pass a*t 127 d*t 0 d*t 0 d*t 1;9999'
                #
                # '^"?(https?|ftp)"?[ ]*(?:\=|\:)[ ]*"?(https?|socks5)\:\/\/(?:([a-zA-Z][-\w]*)(?:\:(\S*))?@)?([^\:]+)(?:\:'
                #   '([0-9]{2,5}))?"?$'
                v = re.split(
                    r"^"
                    # schema
                    r'(?:"?(https?|ftp)'
                    r'"?[ ]*(?:\=|\:)[ ]*)?"?'
                    # schema_p
                    r"(https?|socks5)\:\/\/"
                    # user + pswd (optional, must not contain ":@ )
                    r"(?:([a-zA-Z][-\w]*)(?:\:(\S*))?@)?"
                    # host
                    r"([^\:]+)"
                    # port (optional)
                    r'(?:\:([0-9]{2,5}))?"?'
                    r"$",
                    p.strip(),
                )

                start = v[0]
                schema = v[1]
                schema_p = v[2]
                user = v[3] if v[3] is not None else ""
                pswd = v[4] if v[4] is not None else ""
                host = v[5]
                port = v[6] if v[6] is not None else ""
                end = v[7]

                if schema is None:
                    schema = "https"

                if schema in proxies:
                    raise BaseException(f"Duplicate proxy entry for protocol {schema}")

                if start != "" or end != "":
                    raise BaseException("Bad proxy expression")

                # Validate host separately
                if not self._matchHost(host):
                    raise BaseException(f'Bad host name "{host}" in proxy expression')

                if int(port) < 0 or int(port) > 65535:
                    raise BaseException("Bad port number in proxy expression")

                proxy = {"schema_p": schema_p, "user": user, "pswd": pswd, "host": host, "port": port}
                proxies[schema] = proxy
            except Exception as ex:
                raise BaseException(f"Bad proxy expression {ex!s}")
            except BaseException as ex:
                raise ex
        return proxies

    # From user multi-string to param dict
    def _getProxies(self, s):
        proxies = {}
        proxies_pswd = ""
        pxd = self._parseProxies(s)
        for k, p in pxd.items():
            v = "{}://{}:{}@{}:{}".format(p["schema_p"], p["user"], p["pswd"], p["host"], p["port"])  # pragma: allowlist secret
            if v[-1] == ":":
                # Empty port
                v = v[:-1]
            if ":@" in v:
                # Empty password
                v = v.replace(":@", "@")
            if "/:" in v:
                # Empty user
                v = v.replace(":@", "@")
                v = v.replace("/:", "/")

            # Keep the passwords as a concatenated string separately for saving to the secure storage
            # NOTE The dictionary insertion order is maintained in Python 3.6 and up (no need to use OrderedDict)
            proxies[k] = "{}://{}@{}:{}".format(p["schema_p"], p["user"], p["host"], p["port"])
            proxies_pswd += MULTI_PSWD_SEP_CHAR + p["pswd"]
        return (proxies, proxies_pswd[1:]) if proxies != {} else (None, None)

    @staticmethod
    def _mergeProxiesPswd(proxies, pswds):
        if proxies is None:
            return None

        ps = pswds.split(MULTI_PSWD_SEP_CHAR)
        return {k: p.replace("@", ":" + ps[i] + "@") for i, (k, p) in enumerate(proxies.items())}

    def _getMergedProxies(self, s):
        proxies, pswd = self._getProxies(s)
        return ConfigForward._mergeProxiesPswd(proxies, pswd)

    def _updateAndWaitForStatus(self, condition, rform):
        # Get the user inputs (validated already)
        auth_token = str(rform["auth_token"])
        username = str(rform["username"])
        password = str(rform["password"])
        log_interval = int(rform["log_interval"])
        api_url = str(rform["api_url"])
        proxies, proxies_pswd = self._getProxies(str(rform["proxies"]))
        sink_url = str(rform["sink_url"])

        # Override only the ones modified in the UI keeping the config ones in effect (if a different set)
        logTypes = [lt for lt in self.log_types]

        for lt in [
            GC_LOGTYPE_ACCESS,
            GC_LOGTYPE_ADMIN,
            GC_LOGTYPE_CLOUDAUDIT,
            GC_LOGTYPE_SWGWEB,
            GC_LOGTYPE_SWGWEBDLP,
            GC_LOGTYPE_HEALTHPROXY,
            GC_LOGTYPE_HEALTHAPI,
            GC_LOGTYPE_HEALTHSYSTEM,
            GC_RESETTIME,
        ]:
            if len(rform.getlist(lt)):
                if lt == "resettime":
                    reset_time = "reset"
                else:
                    if lt not in logTypes:
                        logTypes += [lt]
            else:
                if lt == "resettime":
                    reset_time = ""
                else:
                    if lt in logTypes:
                        logTypes.remove(lt)

        logTypes.sort()
        auth_type = len(rform.getlist("auth_type"))
        use_proxy = len(rform.getlist("use_proxy"))

        app.logger.info(str("POST {} {} {} {}".format("auth_token", ", ".join(logTypes), log_interval, api_url)))

        # Assume update is needed if first time
        isChanged = True
        if all(
            a()
            for a in [
                lambda: self.updateCount > 0,
                # Don't care b/c not saved anyways
                # and self._auth_type == True if auth_type == 'on' or auth_type == 'True' else False
                # and self._use_proxy == True if use_proxy == 'on' or use_proxy == 'True' else False
                #
                # Not saved but need to check authentication to update status
                lambda: self._auth_token.secret == auth_token,  # type: ignore[union-attr]
                lambda: self._username == username,
                lambda: self._password.secret == password,  # type: ignore[union-attr]
                lambda: self._proxies_pswd.secret == proxies_pswd,  # type: ignore[union-attr]
                #
                lambda: self.log_types == logTypes,
                lambda: self.log_interval == log_interval,
                lambda: self.api_url == api_url,
                lambda: self.proxies == proxies,
                lambda: self.sink_url == sink_url,
                lambda: self._reset_time == reset_time,
            ]
        ):
            # return False
            isChanged = False

        # Update the data under thread lock
        # Do it to signal the poll thread to refresh the logs, even if no settings changed
        isSaved = False
        with self._lock(condition):
            self._auth_type = auth_type in ["on", "True"]
            self._use_proxy = (use_proxy in ["on", "True"]) and proxies is not None
            self._auth_token.secret = auth_token  # type: ignore[union-attr]
            self._username = username
            self._password.secret = password  # type: ignore[union-attr]
            self._proxies_pswd.secret = proxies_pswd  # type: ignore[union-attr]
            self.log_types = logTypes
            self.log_interval = log_interval
            self.api_url = api_url
            self.proxies = proxies
            self.sink_url = sink_url
            self._reset_time = reset_time

            self._calculateOptions()

            # Since the polling thread might update some (rare) settings for certain integrations
            # like reset_fence, do the save under the lock (otherwise it wouldn't be necessary)
            if self._isForeignConfigStore() and isChanged:
                # Actually, should never end up here since for those cases
                # the saving is done by alternative client code to alternative config store
                self._save()  # pylint: disable=E1102
                isSaved = True

        if isChanged:
            # Need to save it for printing status on refresh correctly (relative to changes in settings rather than the latest
            # refresh)
            self.updateCountChanged = self.updateCount

            # Save across sessions without blocking on I/O
            if not isSaved:
                self._save()  # pylint: disable=E1102

            # Wait for the update to come through but only if there were changes as a compromise.
            # If there are no changes the page info likely won't be up-to-date to avoid the wait,
            # refreshing multiple times would get the "latest" status eventually.
            # The wait time is a context switch + up to 5 (number of log types) API requests
            # TODO JS: The status could be updated continuously in the background AJAX-style
            self._waitForStatus(self.postTimeoutChanged)
        else:
            # Disabled by default to reduce the confusion from excessive "In progress" status and
            # to avoid the additional wait from network and data processing latency on refresh
            if self.postTimeoutRefresh > 0:
                self._waitForStatus(self.postTimeoutRefresh)

        return isChanged

    def _parseApiUrl(self, url):
        badMatch = ""
        host = None
        api_ver = None

        m = re.search(r"https\:\/\/portal\.((?:us\.)?.+)\/api\/bitglassapi(?:\/(?:logs(?:\/(?:\?cv=(\d\.\d\.\d))?)?)?)?", url)
        if m is None:
            # TODO Do not require auth_token in syslog source case
            # Allow for localhost:514 etc. source but ONLY in LSS app
            if self._isEnabled("bitglass") or self._isEnabled("debug"):
                try:
                    isSyslog = "://" not in url and len(url.split(":")) == 2
                    if isSyslog:
                        host, port = url.split(":")
                        if all(a() for a in [lambda: self._matchHost(host), lambda: int(port) >= 0 and int(port) <= 65535]):
                            return (badMatch, host, api_ver)
                except Exception:
                    return (badMatch, host, api_ver)

            return (badMatch, host, api_ver)

        if m.end() < len(url):
            badMatch = url[m.end() :]
            return (badMatch, host, api_ver)

        h = m.group(1)
        if h is not None and self._matchHost(h):
            host = h

        v = m.group(2)
        if v is not None:
            api_ver = v

        return (badMatch, host, api_ver)

    def _calculateOptions(self):
        _, host, api_ver = self._parseApiUrl(self.api_url)

        if host is not None:
            self.host = host

        if api_ver is not None:
            self.api_ver = api_ver
        else:
            # Restore to default
            self.api_ver = self._api_version_max

        addr_host, addr_port = self.sink_url.split(":")
        if all(
            a()
            for a in [
                lambda: "_qradarConsoleAddress" in self.__dict__,
                lambda: any(
                    b()
                    for b in [
                        lambda: addr_host == "localhost",
                        lambda: addr_host == "127.0.0.1",
                        lambda: all(
                            c()
                            for c in [
                                lambda: ".0.0." in addr_host,
                                lambda: addr_host[0] == "0",
                                lambda: addr_host[-1] == "0",
                                lambda: len(addr_host) == 7,
                            ]
                        ),
                    ]
                ),
            ]
        ):
            # NOTE  ^^^ Workaround for a false security scan medium error
            #       instead of: addr_host == '0.0.0.0')):
            addr_host = self._qradarConsoleAddress  # type: ignore[attr-defined]    # pylint: disable=E1101
        self._syslogDest = (addr_host, int(addr_port))
