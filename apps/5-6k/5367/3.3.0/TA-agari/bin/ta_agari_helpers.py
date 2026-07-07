from datetime import datetime
import sys
import time
import requests
import splunk
from collections import OrderedDict
from splunk import admin
from splunk import rest
from solnlib import conf_manager
import os
import json
import six
try:
    from splunk.clilib import cli_common as cli
except ImportError:
    pass

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
TIMESTAMP_FORMAT_NOFRAC = "%Y-%m-%dT%H:%M:%SZ"
TIMESTAMP_FORMAT_THREAT_FEED_SUBMISSIONS = "%Y-%m-%dT%H:%M:%S%z"
TIMESTAMP_FORMAT_NOTIME = "%Y-%m-%d"
AGARI_SETTINGS_CONF = "agari_settings"
USER_AGENT = "AgariSplunk BP_PD_PR_Integration/v3.3.0"

def get_splunk_version(session_key):
    url = '/server/info?output_mode=json'
    try:
        response, content = splunk.rest.simpleRequest(
            url, sessionKey=session_key, getargs=None, method="GET", raiseAllErrors=True)
        
        version = json.loads(content).get("generator",{}).get("version","")
        return version
    except Exception as ex:
        raise ex

def message_data_ingestion(helper, ew, api_data, index, source, sourcetype):
    event = helper.new_event(data=json.dumps(api_data), time=api_data["event_ts"], host=None, index=index,source=source, sourcetype=sourcetype, done=True,unbroken=True)
    ew.write_event(event)

def splunk_data_ingestion(helper, ew, api_data, index, source, sourcetype):
    if api_data:
        for values in list(api_data.values()):
            for data in values:
                if not data:
                    continue
                event = helper.new_event(data=json.dumps(data), time=data["event_ts"], host=None, index=index,source=source, sourcetype=sourcetype, done=True,unbroken=True)
                ew.write_event(event)
        return True
    else:
        return True

def get_agari_configs():
    cfg = cli.getConfStanza('agari_settings', 'agari_configs')
    return cfg

def get_verify_configs(helper):
    cfg = get_agari_configs()
    verify = cfg.get('verify', True)
    ca_bundle_path = cfg.get('ca_bundle_path', "")
    if ca_bundle_path.strip()!="":
        if ca_bundle_path != "" and not os.path.exists(ca_bundle_path):
            helper.log_error(
                "The file or folder specified by the 'ca_bundle_path' option does not exist: %s. Setting up the verify flag as True"
                % ca_bundle_path
            )
            return True
        return ca_bundle_path
    elif str(verify).lower() in ["t", "true", "1"]:
       return True
    else:
       return False

def get(helper, access_token, url, key, params={}):
    # get an API resource
    proxy_uri = helper._get_proxy_uri()
    proxy_dict = {'http': proxy_uri, 'https': proxy_uri}
    verify = get_verify_configs(helper)
    session_key = helper.context_meta["session_key"]
    splunk_version = ""
    try:
        splunk_version = get_splunk_version(session_key)
    except Exception as ex:
        helper.log_error("There are some errors while getting Splunk version:{}".format(ex))
    FINAL_USER_AGENT = "{} Splunk/v{}".format(USER_AGENT,splunk_version)
    while True:
        try:
            rslt = requests.get(
                url=url,
                params=params,
                headers={"Authorization": "Bearer %s" % access_token, "User-Agent": str(FINAL_USER_AGENT)},
                proxies=proxy_dict,
                verify=verify,
            )
            helper.log_debug("Response got for from Agari server for url: {}. Status Code: {}".format(url, rslt.status_code))
            if rslt.status_code == 200:
                data = rslt.json()
                helper.log_debug("Response 200 got from Agari server for url: {}".format(url))
                return data[key]
            elif rslt.status_code == 429:
                # rate limit response - back-off and try again
                helper.log_debug("Response 429 got from Agari server for url: {}. Sleeping for sometime.".format(url))
                time.sleep(0.1)
                continue
            else:
                try:
                    msg = rslt.json()["error_description"]
                except Exception:
                    msg = rslt.text
                helper.log_error(
                    "API error: [%d] %s: %s" % (rslt.status_code, msg, rslt.url)
                )
                return None
        except Exception as e:
            helper.log_error("API exception: %s" % str(e))
            sys.exit(2)

def get_index(helper, access_token, url, key, params=None, chunk=False):
    params = params or {}
    # process a #index (list) request
    list = []
    limit = None
    if "limit" in params:
        limit = int(params["limit"])
        # a negative limit indicates no paging
        if limit < 0:
            params.pop("limit")
    params["offset"] = 0
    while True:
        rslt = get(helper, access_token, url, key, params=params)
        if not rslt or len(rslt) == 0:
            break
        if chunk:
            yield rslt
        list += rslt
        if limit:
            if limit < 0 or len(rslt) < limit:
                break
            else:
                params["offset"] += limit
        else:
            params["offset"] += len(rslt)
    if not chunk:
        yield list

def timestamp(time=None, as_datetime=False, timestamp_format=None):
    _time = time
    if not time:
        _time = datetime.utcnow()
    else:
        fmt = None
        if timestamp_format:
            fmt = timestamp_format
        elif isinstance(time, str) or isinstance(time, six.text_type):
            if ":" not in time:
                fmt = TIMESTAMP_FORMAT_NOTIME
            elif "." not in time:
                fmt = TIMESTAMP_FORMAT_NOFRAC
            else:
                fmt = TIMESTAMP_FORMAT
        if fmt:
            if fmt == TIMESTAMP_FORMAT_THREAT_FEED_SUBMISSIONS:
                # Python2 doesn't support %z reliably, so catch strptime if it fails:
                try:
                    _time = datetime.strptime(str(time), fmt)
                except ValueError:
                    # ValueError: 'z' is a bad directive in format '%Y-%m-%dT%H:%M:%S%z'
                    time_without_tz = datetime.strptime(
                        time[0:19], TIMESTAMP_FORMAT_THREAT_FEED_SUBMISSIONS[0:17]
                    )
                    if time[20] == "+":
                        time_without_tz -= timedelta(
                            hours=int(time[21:24]), minutes=int(time[25:])
                        )
                    elif time[2] == "-":
                        time_without_tz += timedelta(
                            hours=int(time[21:24]), minutes=int(time[25:])
                        )
                    _time = time_without_tz
            else:
                _time = datetime.strptime(str(time), fmt)
    if as_datetime:
        return _time
    else:
        return datetime.strftime(_time, TIMESTAMP_FORMAT)

def remove_empty(data):
    # recursively removes empty elements from a dict structure
    REM_LINKS = False
    # list() to avoid modifying dict while iterating over it.
    if isinstance(data, dict):
        for k, v in list(data.items()):
            if v is None or v == [] or v == "":
                del data[k]
            if REM_LINKS and k in ["links", "failure_samples_link"]:
                del data[k]
            if isinstance(v, list):
                for _v in v:
                    remove_empty(_v)
    return data

def encapsulate_event(event_type, event_data, ts_field=None, alert_id=None, options=None, direct_ts_value=None):
    options = options or {}
    if event_data == {} or event_data == []:
        return None
    if ts_field:
        if options.get("timestamp_format"):
            ts = timestamp(event_data[ts_field], False, options["timestamp_format"])
        else:
            if isinstance(event_data, dict) and ts_field in event_data:
                ts = timestamp(event_data[ts_field])
            elif isinstance(event_data, list):
                for _event_data in event_data:
                    if ts_field in _event_data:
                        ts = timestamp(_event_data[ts_field])
                        break
    else:
        ts = timestamp()
    if direct_ts_value:
        ts = direct_ts_value
    event = OrderedDict()
    event["event_ts"] = ts
    event["event_type"] = event_type
    event["event_data"] = event_data
    if alert_id:
        event["alert_id"] = alert_id
    return remove_empty(event)

def auth(helper, api_host, client_id, client_secret, api_version="v1/cp"):
    # authenticate with the API
    retry_cnt = 0
    verify = get_verify_configs(helper)
    while True:
        try:
            if api_version == "v1/ep" or api_version == "v1/apr":
                host = "/".join([api_host, api_version, "token"])
            else:
                host = "/".join([api_host, api_version,  "oauth", "token"])
            params="client_id={}&client_secret={}".format(client_id, client_secret)
            headers = {"accept": "application/json", "content-type": "application/x-www-form-urlencoded", "User-Agent": str(USER_AGENT)}
            rslt = helper.send_http_request(host, "POST", payload=params,
                                          headers=headers, 
                                          cookies=None, verify=verify, cert=None,
                                          timeout=60, use_proxy=True)
            helper.log_debug("Response got for auth call. Status Code: {}".format(rslt.status_code))
            if rslt.status_code == 200:
                helper.log_debug("Response 200 got for auth call.")
                return rslt.json()["access_token"]
            elif rslt.status_code == 429:
                retry_cnt += 1
                if retry_cnt == 5:
                    helper.log_info("Auth retries reached 5: continuing to retry")
                elif retry_cnt == 10:
                    helper.log_error("Auth retries exeeded 10: aborting")
                    sys.exit(2)
                sleep(1.0)
                continue
            else:
                try:
                    msg = rslt.json()["error_description"]
                except (ValueError, Exception):
                    msg = rslt.text
                url = re.sub(r"client_secret=\w*", "client_secret=###", rslt.url)
                helper.log_error(
                    "Auth error: [%d] %s: %s" % (rslt.status_code, url, msg)
                )
                sys.exit(2)
        except Exception as e:
            # remove client_secret from exception error message
            sys.exit(2)
