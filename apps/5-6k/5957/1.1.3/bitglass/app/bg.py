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
# File: app/bg.py
#
# Author: alexeiyur AT g m 4 i l . c 0 m
# Licensed under the MIT License (https://mit-license.org/)

import base64
import copy
import json
import os
import socketserver
import time
from datetime import datetime, timedelta
from threading import Condition, Thread
from urllib.error import HTTPError

import requests
from requests.auth import AuthBase, HTTPBasicAuth

import app
from app.config import open_atomic, setPythonLogging, setPythonLoggingLevel, versionTuple
from app.configForward import ConfigForward, log_types

# This is the inconvenience to keep the static security scanners happy (could have used import * instead)
from app.consts import (
    GC_FIELD_INGESTEDTIME,
    GC_FIELD_INITIALTIME,
    GC_FIELD_LOGTYPE,
    GC_FIELD_NEXTPAGETOKEN,
    GC_LOGTYPE_ACCESS,
    GC_LOGTYPE_ADMIN,
    GC_LOGTYPE_CLOUDAUDIT,
    GC_LOGTYPE_CLOUDSUMMARY,
    GC_LOGTYPE_HEALTHAPI,
    GC_LOGTYPE_HEALTHPROXY,
    GC_LOGTYPE_HEALTHSYSTEM,
    GC_LOGTYPE_SWGWEB,
    GC_LOGTYPE_SWGWEBDLP,
)
from app.env import UpdateDataPath, datapath, loggingpath
from app.logevent import pushLog


# from threading import get_ident


conf = None
lastLogFile = None


# For now, just using the token, never need to get/refresh one automatically (by using requests_oauthlib)
class OAuth2Token(AuthBase):
    def __init__(self, access_token):
        self.access_token = access_token

    def __call__(self, request):
        request.headers["Authorization"] = f"Bearer {self.access_token}"
        return request


def ingestLogEvent(ctx, d, address, logTime):
    if ctx and ctx.ctx is not None:
        ctx.ctx.bgPushLogEvent(d, address, logTime)

    # TODO Prevent recursion sending to itself with syslog socket
    return pushLog(d, address, logTime)


def flushLogEvents(ctx):
    if ctx and ctx.ctx is not None:
        ctx.ctx.bgFlushLogEvents()


def Initialize(ctx, datapath=datapath, skipArgs=False, _logger=None, _conf=None, context=None):
    global conf
    global lastLogFile

    # Monkey patch env.datapath first with the value from the command line to read bg json configs
    updatepath = False
    if datapath:
        updatepath = UpdateDataPath(datapath)

    if not app.logger and not _logger:
        app.logger = setPythonLogging(None, datapath)

    if not datapath:
        # Put in the same directory as the logging file (the latter would be well-defined, without uuids)
        datapath = os.path.split(loggingpath)[0] + os.sep
        updatepath = UpdateDataPath(datapath)
        if updatepath:
            conf = None

    if not conf or updatepath:
        if not _conf:
            conf = ConfigForward(context)
            # Be sure to update the logging level once the config is loaded
            setPythonLoggingLevel(app.logger, conf)

            if not skipArgs or conf._isEnabled("debug"):
                # Parse and apply command line options. Always process for a local dev run ('debug'), it's compatible
                conf._applyOptionsOnce()
        else:
            conf = _conf

    # Override the configuration
    if ctx and ctx.ctx is not None:
        # Override the config settings and disable daemon mode for explicit cli context
        ctx.ctx.bgLoadConfig(conf)
        conf._isDaemon = False  # type: ignore[union-attr]
    conf._calculateOptions()  # type: ignore[union-attr]

    if not lastLogFile or updatepath:
        cnf = _conf or conf

        # For Splunk app upgrade, manually 'cp lastlog.json ../local/' before upgrading to ingest incrementally
        # This is because it was saved in default/ in the previous version 1.0.8 and default/ is yanked during upgrade
        folder = cnf._folder  # type: ignore[union-attr]
        if (os.path.sep + "default") in cnf._folder:  # type: ignore[union-attr]
            folder = os.path.join(folder, "..", "local", "")

        lastLogFile = LastLog(os.path.join(folder, "lastlog"), context)

    return conf


class SyslogUDPHandler(socketserver.BaseRequestHandler):
    kwargs = None
    callback = None

    @classmethod
    def start(cls, callback, host, port=514, poll_interval=0.5, **kwargs):
        cls.kwargs = kwargs
        cls.callback = callback
        # TODO Test exception propagation to the main thread (due to a bad host?), may need handling
        try:
            server = socketserver.UDPServer((host, port), cls)
            server.serve_forever(poll_interval=poll_interval)
        except (OSError, SystemExit):
            raise
        except KeyboardInterrupt:
            app.logger.info("Crtl+C Pressed. Shutting down.")

    def handle(self):
        # logger = self.kwargs['logger']
        data = bytes.decode(self.request[0].strip())

        # Strip the string and convert to json
        try:
            conf = self.kwargs["conf"]  # type: ignore[index]
            condition = self.kwargs["condition"]  # type: ignore[index]

            s = f"{conf.customer.lower()} :{{"
            start = data.find(s) + len(s) - 1
            end = data.rfind("}") + 1
            logData = json.loads('{"response":{"data":[' + data[start:end] + "]}}")

            with conf._lock(condition, notify=False):
                transferLogs(None, logTypes=None, logData=logData, **self.kwargs)  # type: ignore[misc]  # pylint: disable=E1134

        except Exception as ex:
            app.logger.warning(f'{ex!s}\n - Discarded bad event message in syslog stream:\n"{data}"\n- from sender {self.client_address[0]}')
            return


TIME_FORMAT_URL = "%Y-%m-%dT%H:%M:%SZ"
TIME_FORMAT_LOG = "%d %b %Y %H:%M:%S"
TIME_FORMAT_ISO = "%Y-%m-%dT%H:%M:%S.%fZ"


def strptime(s):
    # For more reliable (but slower) datetime parsing (non-English locales etc.) use:
    # pip install python-dateutil
    # from dateutil import parser
    # parser.parse("Aug 28 1999 12:00AM")  # datetime.datetime(1999, 8, 28, 0, 0)
    # '06 Nov 2018 08:15:10'

    return datetime.strptime(s, TIME_FORMAT_LOG)


class LastLog:
    def __init__(self, fname, context=None, shared=None, logtype=""):
        self.fname = f"{fname}-{logtype}.json" if shared else f"{fname}.json"
        self.shared = shared
        self.log = {}
        self.logtype = logtype
        self.subLogs = {}
        self.context = context
        try:
            if self.context is not None:
                # No file system, also may be flat (the old format). That's Demisto limitation so far
                self.log = (
                    (
                        ({logtype: json.loads(context[logtype])} if isinstance(context[logtype], str) else {logtype: context[logtype]})
                        if logtype in context
                        else {logtype: {}}
                    )
                    if self.shared
                    else dict(context)
                )
            else:
                with open(self.fname) as f:
                    self.log = json.load(f)

            if self.shared is None:
                # This is a shared (old) file (or string-only context). Convert to the new format if needed
                for lt in log_types:
                    if self.get(logtype=lt) and isinstance(self.log[lt], str):
                        self.log[lt] = json.loads(self.log[lt])
        except Exception as ex:
            app.logger.info(f"{ex!s}\n - Last log file {self.fname} not found")
            lastLog = {}
            if self.shared:
                lastLog[logtype] = self.shared.log[logtype]
            else:
                for lt in log_types:
                    lastLog[lt] = {}
            self.log = lastLog

        # Create children one per log type unless sharing the same file for all
        if self.shared is None:
            for lt in log_types:
                self.subLogs[lt] = LastLog(fname, context, self, lt)

    def dump(self):
        try:
            if self.context is not None:
                # Don't assume it has to be converted to string, maybe some platform support nested context (unlike Demisto)
                # The save() method below will take care of that and merging different log types
                self.context[self.logtype] = self.log[self.logtype]
                self.context.save()
            else:
                with open_atomic(self.fname, "w") as f:
                    json.dump(self.log, f, indent=4, sort_keys=True)
        except Exception as ex:
            app.logger.error(f"Could not save last log event across app sessions: {ex}")

    def get(self, field=None, logtype=None):
        if logtype is None:
            logtype = self.logtype
        elif logtype in self.subLogs:
            return self.subLogs[logtype].get(field)

        if logtype not in self.log or self.log[logtype] == {}:
            return False

        if field:
            ll = self.log[logtype]
            # Handle the old format to be forward compatible across upgrade
            res = json.loads(ll) if isinstance(ll, str) else ll
            return res[field] if field in res else None

        return True

    def getHistoricLogTypeList(self):
        return [lt for lt in log_types if self.get(logtype=lt)]

    def update(self, dtime, ll, logtype=None):
        if logtype is None:
            logtype = self.logtype
        elif logtype in self.subLogs:
            return self.subLogs[logtype].update(dtime, ll)

        if ll:
            # Add extra fields for diagnostics. Should not lag event log timestamp more than by the API polling interval
            ll[GC_FIELD_INGESTEDTIME] = datetime.utcnow().strftime(TIME_FORMAT_LOG)

            # For diagnostics purposes (for some weird cases of limited SIEM license issues or deployment irregularities etc.),
            # keep the earliest (initial) timestamp of past requests starting from the most recent reset (log rewind)
            # This way we can prove that the missing data is due to some SIEM platform vagary rather than our bug
            it = self.get("_initialtime", logtype)
            if it:
                # Copy over, this never changes unless logs get rewound
                ll[GC_FIELD_INITIALTIME] = it
            else:
                # This is the first successful save
                ll[GC_FIELD_INITIALTIME] = dtime.strftime(TIME_FORMAT_LOG)

            self.log[logtype] = ll
            self.dump()
        else:
            # This is a successful request with empty (exhausted) data so use the last one but handle the (corner) case
            # of error logged inbetween (coinsiding with app relaunch) by clearing the error entries if there are any
            if self.get(logtype=logtype):
                if self.get("_failedtime", logtype):
                    del self.log[logtype]["_failedtime"]
                if self.get("_errormessage", logtype):
                    del self.log[logtype]["_errormessage"]

        if logtype in self.log:
            return json.dumps(self.log[logtype])
        else:
            return ""

    def updateError(self, conf, errormsg, resettime, logtype=None):
        if logtype is None:
            logtype = self.logtype
        elif logtype in self.subLogs:
            return self.subLogs[logtype].updateError(conf, errormsg, resettime)

        if not self.get(logtype=logtype):
            self.log[logtype] = {}

        # Handle the corner case of never having a successful message ever yet so add the missing time
        # field to make the recovery possible (the data reading code defaults to 'now' in such case to
        # play it safe and avoid the possible data duplication but this leads to never getting
        # good messages unless by fluke of hitting upon a very recent message). Assume the initial
        # data period just the same as the reading code does when starting up.
        # This provides for an alternative hack to reset the log type: edit the file and rename the 'time' field.
        if not self.get("time", logtype) or resettime:
            if self.get("time", logtype):
                # Backup the original 'time' field if present by renaming it first
                self.log[logtype]["_time"] = self.log[logtype]["time"]
            t = datetime.utcnow() + timedelta(seconds=-1 * conf.log_initial) if not resettime else resettime
            self.log[logtype]["time"] = t.strftime(TIME_FORMAT_LOG)

        # Update with failure timestamp and message, keep last ingested success timestamp
        self.log[logtype]["_failedtime"] = datetime.utcnow().strftime(TIME_FORMAT_LOG)
        self.log[logtype]["_errormessage"] = str(errormsg)
        self.dump()

    def clobber(self, resettime=None, logtype=None):
        # Clobbering the children with empty json {} is the simplest and most robust way to go.
        # Actually deleting the file would not be enough as the old format file persist, so
        # implementing it correctly would need atomically updating more than one file which would
        # complicate the code immensely and for Splunk, even the use of temp files is a potential
        # certification problem (although bogus one IMO)
        if logtype is None:
            logtype = self.logtype
        elif logtype in self.subLogs:
            return self.subLogs[logtype].clobber(resettime)

        # Just write bare braces (without adding the log type) keeping it simpler
        # self.log[logtype] = {}
        self.log = {}

        # The softer option of rolling back the time (provided by the UI already for flexibility)
        # TODO Ignore for the simplicity sake until the UI provides the actual reset time
        # if resettime:
        #     self.log[logtype] = {}
        #     self.log[logtype]['time'] = resettime.strftime(TIME_FORMAT_LOG)

        self.dump()


def isOldLogType(lt):
    """Different data order (specific to the storage on the server), npt format etc."""
    return lt in [
        GC_LOGTYPE_ACCESS,
        GC_LOGTYPE_ADMIN,
        GC_LOGTYPE_CLOUDAUDIT,
        GC_LOGTYPE_CLOUDSUMMARY,
        # Old APIs do return health* data (a bug) and npt is in the old format anyways!
        GC_LOGTYPE_HEALTHPROXY,
        GC_LOGTYPE_HEALTHAPI,
        GC_LOGTYPE_HEALTHSYSTEM,
    ]


def getAPIToken(logData, conf, logType):
    if not conf.useNextPageToken:
        return None

    try:
        token = logData["nextpagetoken"]
        d = json.loads(base64.b64decode(token))
    except Exception as ex:
        app.logger.warning(f"Invalid token returned: {token} {ex}")  # nosemgrep
        return None

    if d == {}:
        # Technically, it's an invalid token but this accompanies an empty data set
        return None

    if isOldLogType(logType):
        if "log_id" not in d:
            app.logger.warning(f'No "log_id" encoded in logtype "{logType}" returned token: {token}')  # nosemgrep
            return None

        if "datetime" not in d:
            app.logger.warning(f'No "datetime" encoded in logtype "{logType}" returned token: {token}')  # nosemgrep
            return None
    else:
        if "start_time" not in d:
            app.logger.warning(f'No "start_time" encoded in logtype "{logType}" returned token: {token}')  # nosemgrep
            return None

        if "end_time" not in d:
            app.logger.warning(f'No "end_time" encoded in logtype "{logType}" returned token: {token}')  # nosemgrep
            return None

        if "page" not in d:
            app.logger.warning(f'No "page" encoded in logtype "{logType}" returned token: {token}')  # nosemgrep
            return None

    return token


SKIPPED_REQUEST_ERROR = "UNAUTHORiZED"


def RestParamsLogs(_, host, api_ver, logType, npt, dtime):
    url = ("https://portal." + host) if host else ""
    endpoint = "/api/bitglassapi/logs"

    # Adjust the version upwards to the minimum supported version for new log types as necessary
    # Make sure it's lower before overriding to avoid downgrading the version
    if logType in [GC_LOGTYPE_SWGWEB, GC_LOGTYPE_SWGWEBDLP]:
        if versionTuple(api_ver) < versionTuple("1.1.0"):
            api_ver = "1.1.0"
    elif logType in [GC_LOGTYPE_HEALTHPROXY, GC_LOGTYPE_HEALTHAPI, GC_LOGTYPE_HEALTHSYSTEM]:
        if versionTuple(api_ver) < versionTuple("1.1.5"):
            api_ver = "1.1.5"

    if npt is None:
        urlTime = dtime.strftime(TIME_FORMAT_URL)
        dataParams = f"/?cv={api_ver}&responseformat=json&type={logType!s}&startdate={urlTime}"
    else:
        dataParams = f"/?cv={api_ver}&responseformat=json&type={logType!s}&nextpagetoken={npt}"

    return (url, endpoint, dataParams)


def RestParamsConfig(_, host, api_ver, type_, action):
    url = ("https://portal." + host) if host else ""

    # This is a POST, version is not a proper param, unlike in logs (?? for some reason)
    endpoint = f"/api/bitglassapi/config/v{api_ver}/?type={type_}&action={action}"
    return (url, endpoint)


def restCall(_, url, endpoint, dataParams, auth_token, proxies=None, verify=True, username=None, password=None):
    if dataParams is None:
        dataParams = ""

    # BANDIT    No, this is not a 'hardcoded password'. This is a check if any password supplied by the user.
    if auth_token is None or auth_token == "":  # nosec
        auth_type = "Basic"

        # Must have creds supplied for basic
        if any(a() for a in [lambda: username is None or username == "", lambda: password is None or password == ""]):  # nosec
            # BANDIT    ^^^ No, this is not a 'hardcoded password'. This is a check if any password supplied by the user.
            # Emulate an http error instead of calling with empty password (when the form initially loads)
            # to avoid counting against API count quota
            raise HTTPError(url + endpoint, 401, SKIPPED_REQUEST_ERROR, {}, None)

        auth_token = base64.b64encode((username + ":" + password).encode("utf-8"))
        auth_token = auth_token.decode("utf-8")
    else:
        auth_type = "Bearer"

    # Use requests by default if available
    r = None

    # The authentication header is added below
    headers = {"Content-Type": "application/json"}

    d = {}
    with requests.Session() as s:
        if auth_type == "Basic":
            s.auth = HTTPBasicAuth(username, password)
        else:
            s.auth = OAuth2Token(auth_token)

        if proxies is not None and len(proxies) > 0:
            if isinstance(proxies, dict):
                s.proxies = proxies
            elif proxies[1] is None:
                # Assume a tuple, no passwords provided (or merged in already) - nothing to merge
                s.proxies = proxies[0]
            else:
                # Assume a tuple and merge in the passwords
                s.proxies = ConfigForward._mergeProxiesPswd(proxies[0], proxies[1])

        if isinstance(dataParams, dict):
            # Assume json
            r = s.post(url + endpoint, headers=headers, verify=verify, json=dataParams)
        else:
            # TODO Inject failures (including the initial failure) for testing: raise Exception('test')
            r = s.get(url + endpoint + dataParams, headers=headers, verify=verify)

        r.raise_for_status()
        d = r.json()

    return d, r


def RestCall(_, endpoint, dataParams):
    return restCall(
        _,
        "https://portal." + conf.host,  # type: ignore[union-attr]
        endpoint,
        dataParams,
        conf._auth_token.pswd,  # type: ignore[union-attr]
        (conf.proxies, conf._proxies_pswd.pswd),  # type: ignore[union-attr]
        conf.verify,  # type: ignore[union-attr]
        conf._username,  # type: ignore[union-attr]
        conf._password.pswd,  # type: ignore[union-attr]
    )


def RestCallConfig(_, endpoint, dataParams):
    """Do basic exception handling, just what is necessary for the Bitglass API for integration into SIEM"""
    try:
        return RestCall(_, endpoint, dataParams)
    except Exception as ex:
        msg = f"Bitglass Config API: request {endpoint}({dataParams}) failed with {ex}"
        # Avoid polluting the log if no valid settings have been set yet
        if SKIPPED_REQUEST_ERROR not in msg:
            app.logger.error(msg)

        return {}, ex


def processLogEvents(ctx, conf, logType, data, nextPageToken, logTime, isSyslog):
    # Cover the case of reverse chronological order (in case of not reversing it back)
    lastLog = data[0]

    # Querying API data by 'time' field (not using nextpagetoken) is broken for 1.1.0 log types
    # swgweb and swgwebdlp causing overlaps. So disable the fallback path for them (no nextpagetoken)
    # No fix planned, so this workaround is a keeper
    isOldLt = isOldLogType(logType)
    if nextPageToken is None and not isOldLt and not isSyslog:
        raise ValueError("Invalid page token for swgweb* log types is not supported")

    for d in data[:: -1 if strptime(data[0]["time"]) > strptime(data[-1]["time"]) else 1]:
        # In some new log types like swgweb the data are sorted from recent to older
        # So let's not assume chronological order to be on the safe side..
        tm = strptime(d["time"])

        # Inject logtype field, it's needed by QRadar Event ID definition (defined in DSM editor)
        if GC_FIELD_LOGTYPE not in d:
            d[GC_FIELD_LOGTYPE] = logType

        # NOTE Use logTime if QRadar has problems with decreasing time (as in swgweb and swgwebdlp)
        ingestLogEvent(ctx, d, conf._syslogDest, tm)

        d[GC_FIELD_NEXTPAGETOKEN] = nextPageToken if nextPageToken is not None else ""

        if any(a() for a in [lambda: logTime is None, lambda: tm > logTime, lambda: isOldLt]):
            # ^^^ This is to avoid the possible +1 sec skipping data problem (if no npt)
            logTime = tm
            lastLog = d
            # json.dumps(d, sort_keys=False, indent=4, separators = (',', ': '))

    return logTime, lastLog


def rewindLogEvents(ctx, conf, logType):
    # Must be validated by the app if it's the actual time datetime.datetime
    # TODO Can switch to using format TIME_FORMAT_ISO for conf._reset_time here and in the UI
    dtime = datetime.utcnow() + timedelta(seconds=-1 * conf.log_initial)
    nextPageToken = None

    # Override the last log data with the new 'time' field
    if conf.hardreset:
        # This should be the default.
        # Clobber all the data in the file as the last resort! This is the important fool-proof method for
        # ultimate UI control on the cloud if some bug is suspected to hold new messages etc.
        app.logger.warning(f'Hard-reset for "{logType}" initiated due to user request. The data will resume when new messages get available.')
        lastLogFile.clobber(dtime, logtype=logType)  # type: ignore[union-attr]
    else:
        # The soft reset mode is essential for testing by keeping the state around. It's used for auto-reset as well
        app.logger.warning(f'Soft-reset for "{logType}" initiated due to user request. The data will resume when new messages get available.')
        lastLogFile.updateError(
            conf,
            "Soft-reset initiated due to user request. "  # type: ignore[union-attr]
            "Waiting for the new data becoming available starting from (see the 'time' field below)",
            dtime,
            logType,
        )

    return nextPageToken, dtime


def drainLogEvents(ctx, conf, logType, logData=None, dtime=None, nextPageToken=None):
    status = conf.status[logType]
    r = None

    isSyslog = logData is not None

    if conf._reset_time and not isSyslog:
        nextPageToken, dtime = rewindLogEvents(ctx, conf, logType)

    logTime = dtime

    try:
        raiseBackendError = False
        if raiseBackendError:
            raise Exception("injectbackendfailure")

        i = 0
        drained = False
        while not drained:
            if isSyslog:
                drained = True
            else:
                if i > 0:
                    # This is a crude way to control max event rate for Splunk / QRadar etc. as required
                    # without adding another thread and a queue which is a design over-kill
                    time.sleep(1.0 / conf._max_request_rate)

                if conf.host == conf._default.host:
                    # Avoid the overhead of invalid request even if there is no traffic generated
                    raise HTTPError(conf.host, -2, SKIPPED_REQUEST_ERROR, {}, None)

                # TODO If there is a hint from API that all data is drained can save the
                # split second sleep and the extra request
                url, endpoint, dataParams = RestParamsLogs(None, conf.host, conf.api_ver, logType, nextPageToken, logTime + timedelta(seconds=1))
                logData, r = restCall(
                    None,
                    url,
                    endpoint,
                    dataParams,
                    conf._auth_token.pswd,
                    (conf.proxies, conf._proxies_pswd.pswd),
                    conf.verify,
                    conf._username,
                    conf._password.pswd,
                )
                i += 1

            lastLog = None
            nextPageToken = getAPIToken(logData, conf, logType)

            data = logData["response"]["data"]
            if len(data) == 0:
                drained = True
            else:
                logTime, lastLog = processLogEvents(ctx, conf, logType, data, nextPageToken, logTime, isSyslog)

            status.cntSuccess = status.cntSuccess + 1
            status.lastMsg = "ok"
            if isSyslog:
                status.lastLog = json.dumps(lastLog)
            else:
                status.lastLog = lastLogFile.update(dtime, lastLog, logType)  # type: ignore[union-attr]

            flushLogEvents(ctx)

    except Exception as ex:
        msg = f'Bitglass Log Event Polling: failed to fetch data "{logType!s}": {ex}'
        # If no valid settings have been set, avoid polluting the log
        if SKIPPED_REQUEST_ERROR not in msg:
            app.logger.error(msg)
            r = ex
            lastLogFile.updateError(conf, r, None, logType)  # type: ignore[union-attr]
            status.cntError = status.cntError + 1
            status.lastMsg = str(ex)

        status.lastLog = ""

    # NOTE  Last successful result has empty data now (drained), instead, could merge all data and return
    #       making it optional if ingestLogEvent is not set.. Without it, attaching data to result is rather useless
    status.lastRes = r
    status.lastTime = logTime
    status.updateCount = conf.updateCount

    conf.status["last"] = status

    return logTime


def transferLogs(ctx, conf, condition, logTypes=None, logData=None, dtime=None, npt=None, resetFence=datetime.utcnow().isoformat()):
    myConf = conf._deepcopy()
    condition.release()

    if not logTypes:
        if myConf._reset_time:
            # Pull all the log types that have ever been pulled unless the specific log type list was provided (like in Phantom).
            # Merge with the currently specified ones
            # logTypes = log_types   # All possibly supported log types
            h = lastLogFile.getHistoricLogTypeList()  # type: ignore[union-attr]
            n = myConf.log_types
            logTypes = h + list(set(n) - set(h))  # Whatever have been tried from the last reset plus currently requested
        else:
            logTypes = myConf.log_types  # Only currently requested

    logTime = {}
    if logData is None:
        for lt in logTypes:
            logTime[lt] = drainLogEvents(
                ctx, myConf, lt, logData, dtime[lt] if dtime is not None else None, npt[lt] if npt is not None else None
            )
    else:
        # syslog source
        # Make sure nextpagetoken is disabled
        myConf.useNextPageToken = False
        lt = logData["response"]["data"][0]["logtype"]
        logTime[lt] = drainLogEvents(None, myConf, lt, logData=logData)

    condition.acquire()
    myConf.status["updateCount"] = conf.updateCount

    # Load the latest state for the UI and reset the read-once-reset-to-default config params
    conf.status = copy.deepcopy(myConf.status)
    if conf._reset_time:
        if conf._isForeignConfigStore():
            conf.reset_fence = resetFence
            conf._save()
        conf._reset_time = ""

    # Increment by smallest delta to avoid repeating same entries
    # TODO Using microseconds=1 causes event duplication.. what is the minimum resolution to increment??
    #       without data loss but with guaranteed no repetitions
    if logData is None:
        if conf._isDaemon:
            condition.wait(myConf.log_interval)
        for lt in logTypes:
            dtime[lt] = logTime[lt] + timedelta(seconds=1)


def getLastLogTimeAndNpt(ctx, conf, logTypes=None):
    # Have to complicate things b/c the API doesn't support combining different log types
    dtime = {}
    npt = {}  # type: ignore[var-annotated]
    now = datetime.utcnow()
    for lt in log_types:
        # = datetime.utcnow() + timedelta(days=-1)
        dtime[lt] = now + timedelta(seconds=-1 * conf.log_initial)
        npt[lt] = None

        # Adjust to avoid the overlap with a previous run, warn on a possible gap
        # The gap is caused by either: app down time or the log source being disabled in earlier app run
        # was greater than 30 days (default of 'log_initial')
        try:
            if lastLogFile.get(logtype=lt):  # type: ignore[union-attr]
                try:
                    # Could be missing due to the old file format
                    npt[lt] = lastLogFile.get("nextpagetoken", lt)  # type: ignore[union-attr]
                    if npt[lt] == "":
                        npt[lt] = None
                        app.logger.warning(f"Empty nextpagetoken found for log type {lt} (old lastlog format?)")

                except Exception as ex:
                    npt[lt] = None
                    app.logger.warning(f'Error "{ex!s}" retrieving nextpagetoken for log type {lt}')

                d = strptime(lastLogFile.get("time", lt))  # type: ignore[union-attr]
                if dtime[lt] <= d:
                    dtime[lt] = d
                else:
                    # Important! For a possible gap, discard nextpagetoken loaded from lastlog
                    # NOTE: This still has an extremely remote possibility of data duplication
                    #       (no messages over the gap period is a necessary condition then - unpopulated gap)
                    npt[lt] = None
                    app.logger.warning(
                        f"Possible gap for log type {lt!s} from {d.strftime(TIME_FORMAT_LOG)} to {dtime[lt].strftime(TIME_FORMAT_LOG)}"
                    )
            else:
                app.logger.info(f"No lastlog data found for log type {lt}")

        except Exception as ex:
            # Bad data in lastLogFile? Treat overlap as data corruption so exclude its possibility and warn
            # Discard nextpagetoken loaded from lastlog, also see the comment just above
            npt[lt] = None

            # By just setting it to 'now' the bad data would persist without getting any new messages and
            # hence no chance to reset the data to good format unless due to a fluke of a very recent message.
            # Instead, do a soft reset
            dtime[lt] = now
            app.logger.error(f"Probable gap for log type {lt!s} to {dtime[lt].strftime(TIME_FORMAT_LOG)} due to BAD LAST LOG DATA: {ex}")

            # Re-write the file back to the good format
            # TODO If wishing to reduce missing a lot of data in favor of some overlap,
            #      may rely on the last log file mofification time minus polling period (which one? could have changed)
            app.logger.warning("Auto-reset initiated due to bad last log data. The data will resume when new messages get available.")
            lastLogFile.updateError(
                conf,
                "Auto-reset initiated due to bad last log data. "  # type: ignore[union-attr]
                "Waiting for the new data becoming available starting from (see the 'time' field below)",
                now,
                lt,
            )

            # Should never end up here again unless the file gets invalidated outside the app once more

        if npt[lt] is not None:
            app.logger.info(f'Valid_nextpagetoken "{npt[lt]}" found for log type {lt}')

    return dtime, npt


def PollLogs(ctx, conf, logTypes=None, condition=Condition(), resetFence=datetime.utcnow().isoformat()):
    """
    Pump BG log events from BG API to QRadar
    """

    pid = os.getpid()
    # tid = get_ident()
    tid = 0
    app.logger.info("================================================================")
    app.logger.info(f"Polling: start polling log events.. pid={pid}, tid={tid}")
    app.logger.info("----------------------------------------------------------------")

    isSyslog = all(a() for a in [lambda: "://" not in conf.api_url, lambda: len(conf.api_url.split(":")) == 2])

    res = None
    if isSyslog:
        host, port = conf.api_url.split(":")
        # TODO: At least verify that sink_url is different to reduce the loop possibility sending back to itself
        SyslogUDPHandler.start(transferLogs, host=host, port=int(port), conf=conf, condition=condition)
    else:
        dtime, npt = getLastLogTimeAndNpt(ctx, conf, logTypes)

        with conf._lock(condition, notify=False):
            isDaemon = True
            while isDaemon:
                transferLogs(ctx, conf, condition, logTypes, None, dtime, npt, resetFence)

                # Run only once if not in the daemon mode
                isDaemon = conf._isDaemon

        res = conf.status

    app.logger.info(f"Polling: stop polling log events.. pid={pid}, tid={tid}")
    app.logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    return res


class bitglassapi:
    Initialize = Initialize

    # TODO Implement OverrideConfig(), it will also validate all settings (the validation is to be moved from UI)

    # Low level (overriding settings params)
    restCall = restCall

    RestParamsLogs = RestParamsLogs
    RestParamsConfig = RestParamsConfig

    RestCall = RestCall
    RestCallConfig = RestCallConfig

    # Higher level calls relying on serialized data and synchronization
    PollLogs = PollLogs

    def __init__(self, ctx=None):
        if ctx is None:
            # Use default callbacks
            ctx = self

        self.ctx = ctx

    # Default callbacks command mode without explicit context (like Splunk)
    def bgPushLogEvent(self, d, address, logTime):
        # Additional processing for the script
        from app import cli  # pylint: disable=E0401

        cli.pushLog(d, address, logTime)

    def bgFlushLogEvents(self):
        from app import cli  # pylint: disable=E0401

        cli.flushLogs()

    def bgLoadConfig(self, conf):
        from app import cli  # pylint: disable=E0401

        cli.loadConfiguration(conf)


# Test flat dict context (when file i/o is not available)
# This class gets overridden in the actual platform using such context
class BitglassContext(dict):
    def __init__(self, context={}):
        # Purge the old data
        for k, v in dict(self).items():
            del self[k]
        # Load the new data
        for k, v in context.items():
            self[k] = v

    def save(self):
        # Must convert into flat dict of strings or it's not saved properly
        d = {k: v if isinstance(v, str) else json.dumps(v) for k, v in dict(self).items()}

        # This (test code) runs repeatedly in a thread instead of passing from real framework on repeated script invocation
        # The above means the Initialize() path called only once with empty dict (making it a partial scenario), unlike in Demisto
        self.__init__(d)  # type: ignore[misc]


context = None


# Uncomment for testing flat file-less context like the one used in Demisto
# This is passed to bgapi to keep the lastlog object in since there is no file i/o available
# context = BitglassContext()


def startWorkerThread(conf, isDaemon=True, bgapi=None):
    Initialize(bgapi, _logger=app.logger, _conf=conf, context=context)

    condition = Condition()
    thread = Thread(target=PollLogs, args=(bgapi, conf, None, condition))

    conf._isDaemon = isDaemon
    thread.start()
    if not isDaemon:
        thread.join()
    return condition


# Skip this part for the merged module support
if __name__ == "__main__":
    from app.cli import main

    Initialize(None)

    # Only for debugging full context cli variants so that can use one debug setting for all
    if conf._isEnabled("debug"):
        main(app.logger, conf, bitglassapi)

    # Start the worker thread explicitly if main() above didn't exit()
    startWorkerThread(conf, False, bitglassapi())
