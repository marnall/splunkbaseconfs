# encoding = utf-8

import app_common as utils

import json
import requests
import sys
import traceback
from datetime import datetime
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib.parse import urlparse
import ndjson
import time


APP_VERSION = utils.get_version()
API_PATH = '/v3.0/datalake/dataPipelines'


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

        alert["severity_id"] = str(alert.get("severity", "0"))
        alert["severity"] = alert.get("filterRiskLevel", "undefined")
        if "description" not in alert:
            alert["description"] = alert.get("description", "")
        if "signature" not in alert:
            alert["signature"] = alert.get(
                'detectionName', alert.get('malName', ''))
        if "signature_id" not in alert:
            alert["signature_id"] = alert.get('policyId', '')
        if "id" not in alert:
            alert["id"] = alert.get('uuid', '')
        if "type" not in alert:
            alert["type"] = "event"
        if "dest_type" not in alert:
            alert["dest_type"] = "endpoint"
        if "dest" not in alert:
            if "endpointHostName" in alert:
                alert["dest"] = alert["endpointHostName"]
                if "endpointGUID" in alert:
                    alert["dest"] = alert["dest"] + "," + alert["endpointGUID"]
            if "dest" not in alert:
                alert["dest"] = ""
        if "dest_ip" not in alert:
            alert["dest_ip"] = alert.get("endpointIp", "")
        if "action" not in alert:
            alert["action"] = alert.get("act", "")
        if "date" not in alert:
            alert["date"] = alert.get("eventTimeDT", "")
        if "file_hash" not in alert:
            alert["file_hash"] = alert.get(
                "fileHash", alert.get("fileHashSha256", ""))
        if "file_name" not in alert:
            alert["file_name"] = alert.get("fileName", "")
        if "file_path" not in alert:
            alert["file_path"] = alert.get("filePath", "")
        if "user" not in alert:
            alert["user"] = alert.get(
                "processUser", alert.get("objectUser", ""))
        if "vendor_product" not in alert:
            alert["vendor_product"] = alert.get("pname", "")
        if "product_version" not in alert:
            alert["product_version"] = alert.get("pver", "")
        if "signature_version" not in alert:
            alert["signature_version"] = alert.get("patVer", "")
        if "message_received_time" not in alert:
            if "logReceivedTime" in alert:
                alert["message_received_time"] = alert["logReceivedTime"]

    except Exception as e:
        utils.helper.log_warning(traceback.format_exc())


def collect_events_for_one_consumer(helper, ew, endpoint, token):
    global API_PATH
    cid = utils.extractCID(token)
    STANZA = helper.get_input_stanza_names()
    helper.log_info(
        "[TrendMicro Detections] <%s> get stanza names: %s" % (cid, STANZA))
    parse_url = urlparse(endpoint)
    endpoint = "{}://{}".format(parse_url.scheme, parse_url.netloc)
    helper.log_info(
        "[TrendMicro Detections] <%s> get endpoint: %s" % (cid, endpoint))
    if endpoint == "https://api.xdr.cybereye.gov.ae":
        API_PATH = "/beta/xdr/datalake/dataPipelines"
    https_proxy = str(helper.get_global_setting("https_proxy")).strip()
    backoff_time = float(helper.get_global_setting("backoff_time") or 10)
    helper.log_info(
        "[TrendMicro Detections] <%s> get backoff_time: %d" % (cid, backoff_time))
    
    proxies = {}

    if https_proxy != None and https_proxy.lower() != "none":
        proxies["https"] = https_proxy

    try:
        DetectionPipeline(
            helper,
            endpoint,
            token,
            proxies,
            cid
        )
    except Exception as e:
        helper.log_error("[TrendMicro Detections] <%s> detections exception: %s" % (cid, str(e)))
        return 1

    headers = {
        "x-customer-id": cid,
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(token),
        "User-Agent": "TMDetectionsSplunkAddon/" + str(APP_VERSION)
    }

    ft_str = "%Y-%m-%dT%H:%M:%SZ"
    nowTime = utils.format_iso_time(ft_str, 30)

    file_context = utils.fetch_context(STANZA, cid, {
        'from': nowTime
    })

    query_params = {
        "startDateTime": None,
        "endDateTime": None,
        "top": 500,
    }
    startTime = file_context.get('from', nowTime)
    if isinstance(startTime, int):
        startTime = utils.timestamp2iso(int(startTime), ft_str)

    time_group = utils.timerange_split(startTime, nowTime, 3600)

    request_help = utils.request_help(2, backoff_time)
    pipe_ctx = utils.fetch_context(DetectionPipeline.ctx_name, cid)
    uuid = pipe_ctx.get('pipelineId')
    checkpoint_time = startTime

    try:
        package_bucket = set()
        for start_time, end_time in time_group:
            if start_time == end_time:
                checkpoint_time = end_time
                continue
            curr_bucket = set()
            query_params["startDateTime"] = start_time
            query_params["endDateTime"] = end_time
            helper.log_info(
                "[TrendMicro Detections] <%s> request to detections: %s" % (cid, str(query_params)))
            while True:
                res = request_help(
                    url=f"{endpoint}{API_PATH}/{uuid}/packages",
                    method="GET",
                    parameters=query_params,
                    headers=headers,
                    proxies=proxies
                )
                res.raise_for_status()

                helper.log_info("[TrendMicro Detections] <%s> x-trace-id: %s, response: %s" %
                                (cid, res.headers.get('x-trace-id'), res.text))
                res_data = res.json()
                pk_list = res_data['items']
                next_link = res_data.get('nextLink')
                for package in pk_list:
                    package_id = package['id']
                    if package_id in package_bucket:
                        continue
                    curr_bucket.add(package_id)
                    res = request_help(
                        url=f"{endpoint}{API_PATH}/{uuid}/packages/{package_id}",
                        method="GET",
                        headers=headers,
                        proxies=proxies
                    )
                    res.raise_for_status()
                    res_body = ndjson.loads(res.text)
                    helper.log_info(
                        "[TrendMicro Detections] <%s> package get totalCount: %d" % (cid, len(res_body)))
                    helper.log_info(
                        f"[TrendMicro Detections] <{cid}> events start writing...")
                    for detection in res_body:
                        detection['customerID'] = cid
                        if 'eventTime' in detection:
                            event_time = time.gmtime(int(detection['eventTime'][:-3]))
                            detection["eventTimeDT"] = time.strftime('%Y-%m-%dT%H:%M:%S+00:00', event_time)
                        cim_compliant(detection)
                        event_data = json.dumps(detection)
                        if sys.getsizeof(event_data) > 999999:
                            detection['processCmd'] = "..."
                            event_data = json.dumps(detection)
                        event = helper.new_event(data=event_data, time=datetime.now(),
                                                 host=None, index=helper.get_output_index(), source=helper.get_input_type(),
                                                 sourcetype=helper.get_sourcetype(), done=True, unbroken=True)
                        ew.write_event(event)
                    helper.log_info(
                        f"[TrendMicro Detections] <{cid}> {len(res_body)} events has been written")
                if next_link:
                    query_params["pageToken"] = utils.query_params_parse(next_link)["pageToken"]
                else:
                    break
            checkpoint_time = end_time
            package_bucket = curr_bucket

    except requests.exceptions.HTTPError as e:
        helper.log_error(
            "[TrendMicro Detections] <%s> detections request error: %s %s" % (cid, str(e), str(endpoint)))
        if utils.isotime_delta(startTime, nowTime, ft_str) >= 60*60*24*7:
            checkpoint_time = utils.format_iso_time(ft_str)
        return 1
    except requests.exceptions.Timeout as e:
        helper.log_error(
            "[TrendMicro Detections] <%s> detections request timeout error: %s" % (cid, str(e)))
        if utils.isotime_delta(startTime, nowTime, ft_str) >= 60*60*24*7:
            checkpoint_time = utils.format_iso_time(ft_str)
        return 1
    except Exception as e:
        helper.log_error(
            "[TrendMicro Detections] <%s> detections exception: %s" % (cid, str(e)))
        return 1
    finally:
        utils.update_context(STANZA, cid, 'from', checkpoint_time)

    helper.log_info(
        f"[TrendMicro Detections] <{cid}> events writing completed")
    return 0


def collect_events(helper, ew):
    endpoint = helper.get_arg('global_account')['endpoint']
    tokens = helper.get_arg('global_account')['token']
    if (not endpoint) or (not tokens):
        helper.log_info("[TrendMicro Detection] no valid config, will pass")
        return 0
    tokens = utils.split_token(tokens)
    return_status = 0
    for token in tokens:
        return_status = return_status | collect_events_for_one_consumer(
            helper, ew, endpoint, token)
    return return_status


class DetectionPipeline:
    ctx_name = "Detection_Pipeline_2m85!"

    def __init__(
        self,
        helper,
        endpoint,
        token,
        proxies,
        cid
    ) -> None:
        self.__helper = helper
        self.__endpoint = endpoint
        self.__token = token
        self.__proxies = proxies
        if (not self.__endpoint) or (not self.__token):
            raise Exception('no valid config')
        self.__headers = {
            'Authorization': 'Bearer ' + self.__token,
            'Content-Type': 'application/json;charset=utf-8',
            "User-Agent": "TMXDRSplunkAddon/" + str(APP_VERSION)
        }
        self._cid = cid
        self.registry()

    def registry(self):
        if (not self.__endpoint) or (not self.__token):
            raise Exception('no valid config')
        need_update = False
        pipe_ctx = utils.fetch_context(self.ctx_name, self._cid)
        uuid = pipe_ctx.get('pipelineId')
        res = requests.request(
            url=f"{self.__endpoint}{API_PATH}",
            method="GET",
            headers=self.__headers,
            proxies=self.__proxies
        )
        res.raise_for_status()
        data = res.json()
        for item in data["items"]:
            if item["type"] == "detection" and item["description"] == "TMXDRSplunkAddon":
                if item["id"] != uuid:
                    need_update = True
                uuid = item["id"]
                break
        if uuid is None:
            config = {
                "type": "detection",
                "description": "TMXDRSplunkAddon",
            }
            res = requests.request(
                url=self.__endpoint + API_PATH,
                method="POST",
                headers=self.__headers,
                proxies=self.__proxies,
                json=config
            )
            self.__helper.log_info("[TrendMicro Detections] <%s> request regist to pipeline: %s" % (
                self._cid, json.dumps(config)))
            self.__helper.log_info("[TrendMicro Detections] <%s> x-trace-id: %s, response: %s" %
                                   (self._cid, res.headers.get('x-trace-id'), res.text))
            if res.status_code == requests.codes.created:
                self.__helper.log_info("[TrendMicro Detections] <%s> init register success: %s" % (
                    self._cid, json.dumps(config)))
            else:
                raise Exception("fail to init register")
            location: str = res.headers.get("Location", "")
            uuid = location.split("/")[-1]
            if bool(uuid) == False:
                raise Exception(
                    f"invalid pipeline uuid, headers: {json.dumps(dict(res.headers))}")
            utils.update_context(self.ctx_name, self._cid, 'pipelineId', uuid)

            res = requests.request(
                url=f"{self.__endpoint}{API_PATH}/{uuid}",
                method="GET",
                headers=self.__headers,
                proxies=self.__proxies
            )
        elif need_update:
            utils.update_context(self.ctx_name, self._cid, 'pipelineId', uuid)
