# encoding = utf-8

import app_common as utils

import json
import requests
import traceback
from datetime import datetime
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib.parse import urlparse


APP_VERSION = utils.get_version()


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    try:
        interval = definition.parameters.get('interval', None)
        if interval is not None and int(interval) < 10:
            raise ValueError(
                "The minimum public API access interval cannot be less than 10 seconds.")
    except ValueError as e:
        # Re-raise with same message but cleaner presentation
        raise ValueError(str(e))
    except Exception as e:
        # Log the actual error for debugging
        helper.log_error(f"Validation error: {str(e)}")
        raise ValueError("Validation failed. Please check input configuration.")


def cim_compliant(alert):
    try:
        if "app" not in alert:
            alert["app"] = "trendmicro_v1"
        if "description" not in alert:
            alert["description"] = alert.get("description", "")
        if "signature" not in alert:
            alert["signature"] = alert.get("model", "")
        if "id" not in alert:
            alert["id"] = alert.get("id", "")
        if "type" not in alert:
            alert["type"] = "event"
        if "user" not in alert:
            alert["user"] = alert['customerID']
        if "mitre_technique_id" not in alert:
            techniques = []
            for rule in alert.get("matchedRules", []):
                for filter in rule.get("matchedFilters", []):
                    for technique in filter.get("mitreTechniques", []):
                        techniques.append(technique)
            alert["mitre_technique_id"] = ",".join(techniques)
        if "dest" not in alert:
            entity_ids = []
            for impact in alert["impactScope"]["entities"]:
                entityValue = impact["entityValue"]
                if isinstance(entityValue, dict):
                    entity_ids.append(entityValue.get('name', ''))
                elif isinstance(entityValue, str):
                    entity_ids.append(entityValue)
            alert["dest"] = ",".join(entity_ids)
    except Exception as e:
        utils.helper.log_warning(traceback.format_exc())


def collect_events_for_one_consumer(helper, ew, endpoint, token):
    cid = utils.extractCID(token)
    STANZA = helper.get_input_stanza_names()
    helper.log_info(
        "[TrendMicro XDR] <%s> get stanza names: %s" % (cid, STANZA))
    parse_url = urlparse(endpoint)
    endpoint = "{}://{}".format(parse_url.scheme, parse_url.netloc)
    helper.log_info("[TrendMicro XDR] <%s> get endpoint: %s" % (cid, endpoint))
    https_proxy = str(helper.get_global_setting("https_proxy")).strip()

    backoff_time = float(helper.get_global_setting("backoff_time") or 10)
    helper.log_info("[TrendMicro XDR] <%s> get backoff_time: %d" %
                    (cid, backoff_time))

    proxies = {}

    if https_proxy != None and https_proxy.lower() != "none":
        proxies["https"] = https_proxy

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(token),
            "User-Agent": "TMXDRSplunkAddon/" + str(APP_VERSION)
        }

        # construct time range in payload
        nowTime = utils.format_iso_time("%Y-%m-%dT%H:%M:%SZ")
        params = {}

        params["endDateTime"] = nowTime
        
        file_context = utils.fetch_context(STANZA, cid, {
            'startDateTime': nowTime
        })
        # v2.0 api used
        if "startTime" in file_context:
            params["startDateTime"] = file_context["startTime"].replace(".000", "")
            utils.del_context(STANZA, cid, "startTime")
        else:
            params["startDateTime"] = file_context.get('startDateTime', nowTime)
        params["dateTimeTarget"] = "updatedDateTime"
        params["orderBy"] = "updatedDateTime asc"
        params["showFields"] = "productNames"

        # Skip API call if start and end time are the same to avoid errors
        if params["startDateTime"] == params["endDateTime"]:
            helper.log_info(
                "[TrendMicro XDR] <%s> startDateTime equals endDateTime, skipping API call" % cid)
            utils.update_context(STANZA, cid, 'startDateTime', nowTime)
            return 0

        helper.log_info(
            "[TrendMicro XDR] <%s> request to workbench: %s" % (cid, str(params)))

        request_help = utils.request_help(2, backoff_time)
        url_path = '/v3.0/workbench/alerts'
        req_url = endpoint + url_path

        try:
            while True:
                res = request_help(
                    url=req_url,
                    method="GET",
                    parameters=params,
                    headers=headers,
                    proxies=proxies
                )
                res.raise_for_status()
                json_obj = res.json()
                helper.log_info(
                    "[TrendMicro XDR] <%s> response from workbench: %s" % (cid, str(json_obj)))
                alerts = json_obj["items"]

                helper.log_info(
                    f"[TrendMicro XDR] <{cid}> events start writing...")
                write_count = 0
                for alert in alerts:
                    alert['customerID'] = cid
                    cim_compliant(alert)
                    event_data = json.dumps(alert)
                    event = helper.new_event(data=event_data, time=datetime.now(),
                                             host=None, index=helper.get_output_index(), source=helper.get_input_type(),
                                             sourcetype=helper.get_sourcetype(), done=True, unbroken=True)
                    ew.write_event(event)
                    write_count += 1
                    if not write_count % 2000:
                        helper.log_info(
                            f"[TrendMicro XDR] <{cid}> {write_count} events has been written")
                if write_count % 2000:
                    helper.log_info(
                        f"[TrendMicro XDR] <{cid}> {write_count} events has been written")
                if "nextLink" in json_obj:
                    skip_token = utils.query_params_parse(json_obj["nextLink"])["skipToken"]
                    params["skipToken"] = skip_token
                else:
                    break

        except requests.exceptions.HTTPError as e:
            helper.log_error(
                "[TrendMicro XDR] <%s> workbench request error: %s %s" % (cid, str(e), str(endpoint)))
            return 1
        except requests.exceptions.Timeout as e:
            helper.log_error(
                "[TrendMicro XDR] <%s> workbench request timeout error: %s" % (cid, str(e)))
            return 1
        except Exception as e:
            helper.log_error(
                "[TrendMicro XDR] <%s> workbench exception: %s" % (cid, str(e)))
            return 1

        utils.update_context(STANZA, cid,  'startDateTime', nowTime)
        # utils.update_tpc_metrics(endpoint, headers, proxies)
        helper.log_info(f"[TrendMicro XDR] <{cid}> events writing completed")

    except RuntimeError as e:
        helper.log_error(
            "[TrendMicro XDR] <%s> workbench unknown error: %s" % (cid, str(e)))
        return 1
    return 0


def collect_events(helper, ew):
    endpoint = helper.get_arg('global_account')['endpoint']
    tokens = helper.get_arg('global_account')['token']
    if (not endpoint) or (not tokens):
        helper.log_info("[TrendMicro XDR] no valid config, will pass")
        return 0

    tokens = utils.split_token(tokens)
    return_status = 0
    for token in tokens:
        return_status = return_status | collect_events_for_one_consumer(
            helper, ew, endpoint, token)
    return return_status
