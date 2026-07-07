# encoding = utf-8

import app_common as utils

import json
import requests
import copy
import traceback
import datetime
from urllib.parse import urlparse
import ndjson

APP_VERSION = utils.get_version()
API_PATH = '/v3.0/oat/dataPipelines'

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    try:
        interval = definition.parameters.get('interval', 120)
        if interval is not None:
            if int(interval) < 40:
                raise ValueError(
                    "The minimum public API access interval cannot be less than 40 seconds.")
            if int(interval) >= 60 * 60:
                raise ValueError(
                    "The maximum public API access interval must be less than 3600 seconds.")
        utils.update_context("GLOBAL", None, 'oatSettingModify', 1)
    except ValueError as e:
        # Re-raise with same message but cleaner presentation
        raise ValueError(str(e))
    except Exception as e:
        # Log the actual error for debugging
        helper.log_error(f"Validation error: {str(e)}")
        raise ValueError("Validation failed. Please check input configuration.")


def spread_filters(detection):
    filters_list = []
    if len(detection.get('filters', [])) == 0:
        dcopy_data = copy.deepcopy(detection)
        del dcopy_data['filters']
        cim_compliant(dcopy_data)
        dcopy_data['filter'] = {}
        return [dcopy_data]

    for oat_filter in detection.get('filters', []):
        dcopy_data = copy.deepcopy(detection)
        dcopy_data.pop('filters', None)
        dcopy_data['filter'] = oat_filter
        cim_compliant(dcopy_data)
        filters_list.append(dcopy_data)
    return filters_list


def format_risk_levels(risk_level="medium"):
    query_levels = ["undefined", "info", "low", "medium", "high", "critical"]
    if risk_level not in query_levels:
        risk_level = "medium"
    return query_levels[query_levels.index(risk_level):]


def defined_risk_level(query_levels):
    risk_levels = ["undefined", "info", "low", "medium", "high", "critical"]
    for level in risk_levels:
        if level in query_levels:
            return level
    return "medium"


def cim_compliant(data):
    try:
        data["app"] = "trendmicro_v1"
        detail = data.get("detail", {})
        if "filter" in data:
            data["description"] = data['filter'].get('description', "")
            data["signature"] = data['filter'].get('name', '')
            data["mitre_technique_id"] = ",".join(
                data['filter'].get('techniques', []))
        if "severity" not in data:
            data["severity"] = detail.get("filterRiskLevel", "undefined")
        if "dest" not in data:
            data["dest"] = data.get("entityName", '')
        if "dest_type" not in data:
            data["dest_type"] = data.get("entityType", '')
        if "id" not in data:
            data["id"] = detail.get("uuid", '')
        if "message_received_time" not in data:
            if "logReceivedTime" in detail:
                data["message_received_time"] = detail["logReceivedTime"]
        data["type"] = "event"
        data["user"] = data["customerID"]
    except Exception as e:
        utils.helper.log_warning(traceback.format_exc())


def collect_events_for_one_consumer(helper, ew, endpoint, token):
    global API_PATH
    cid = utils.extractCID(token)
    STANZA = helper.get_input_stanza_names()
    helper.log_info(
        "[TrendMicro OAT] <%s> get stanza names: %s" % (cid, STANZA))
    polling = helper.get_arg('interval')
    helper.log_info("[TrendMicro OAT] <%s> get interval: %s" % (cid, polling))
    risk_level = helper.get_arg('severity')
    helper.log_info("[TrendMicro OAT] <%s> get severity: %s" %
                    (cid, risk_level))
    backoff_time = int(helper.get_global_setting("backoff_time") or 10)
    helper.log_info("[TrendMicro OAT] <%s> get backoff_time: %d" %
                    (cid, backoff_time))
    https_proxy = str(helper.get_global_setting("https_proxy")).strip()

    cid = utils.extractCID(token)
    query_levels = format_risk_levels(risk_level)
    
    proxies = {}

    if https_proxy != None and https_proxy.lower() != "none":
        proxies["https"] = https_proxy

    parse_url = urlparse(endpoint)
    endpoint = "{}://{}".format(parse_url.scheme, parse_url.netloc)
    helper.log_info("[TrendMicro OAT] <%s> get endpoint: %s" % (cid, endpoint))
    if endpoint == "https://api.xdr.cybereye.gov.ae":
        API_PATH = "/v1.0/preview/ath/oat/dataPipelines"
    try:
        oat_util = OATDataPipeline(
            helper,
            endpoint,
            token,
            proxies,
            risk_level,
            cid
        )
    except Exception as e:
        helper.log_error("[TrendMicro OAT] <%s> oat exception: %s" % (cid, repr(e)))
        return 1

    global_ctx = utils.fetch_context("GLOBAL", None)
    if global_ctx.get('oatSettingModify', 0) == 1:
        oat_util.update(risk_level)
    else:
        oat_setting = oat_util.get_setting()
        helper.log_info("[TrendMicro OAT] <%s> get registered config: %s" % (
            cid, json.dumps(oat_setting)))
        cloud_risk_level = defined_risk_level(oat_setting['riskLevels'])
        if cloud_risk_level != risk_level:
            helper.log_info(
                "[TrendMicro OAT] <%s> sync with cloud config" % (cid))
            utils.set_input_setting(
                f'trendmicro_v1_observed_attack_techniques://{STANZA}', 'severity', cloud_risk_level)

    ft_str = "%Y-%m-%dT%H:%M:%SZ"
    nowTime = utils.format_iso_time(ft_str, 30)

    file_context = utils.fetch_context(STANZA, cid, {
        'startTime': nowTime
    })

    query_params = {}
    # query_params = {'start': '1618045942', 'end': '1618132342', 'size': 200}

    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json;charset=utf-8',
        "User-Agent": "TMXDRSplunkAddon/" + str(APP_VERSION)
    }

    startTime = file_context.get('startTime', nowTime)
    if not startTime.endswith('Z'):
        startTime = utils.timestamp2iso(int(startTime), ft_str)
    time_group = utils.timerange_split(startTime, nowTime, 3600)

    request_help = utils.request_help(2, backoff_time)
    checkpoint_time = startTime
    pipe_ctx = utils.fetch_context(OATDataPipeline.ctx_name, cid)
    uuid = pipe_ctx.get('pipelineId')

    try:
        package_bucket = set()
        for start_time, end_time in time_group:
            # Skip if start and end time are the same to avoid API errors
            if start_time == end_time:
                checkpoint_time = end_time
                continue
                
            curr_bucket = set()
            query_params["startDateTime"] = start_time
            query_params["endDateTime"] = end_time

            helper.log_info("[TrendMicro OAT] <%s> request to oat: %s" % (
                cid, str(query_params)))

            while True:
                res = request_help(
                    url=f"{endpoint}{API_PATH}/{uuid}/packages",
                    method="GET",
                    parameters=query_params,
                    headers=headers,
                    proxies=proxies
                )
                res.raise_for_status()

                helper.log_info("[TrendMicro OAT] <%s> x-trace-id: %s, response: %s" %
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
                    write_count = 0
                    helper.log_info(
                        f"[TrendMicro OAT] <{cid}> events start writing...")
                    for detection in res_body:
                        detection['customerID'] = cid
                        for filter in spread_filters(detection):
                            if filter.get('severity', "undefined") not in query_levels:
                                continue
                            event = helper.new_event(source=helper.get_input_type(), time=datetime.datetime.now(),
                                                     host=None, index=helper.get_output_index(),
                                                     sourcetype=helper.get_sourcetype(), data=json.dumps(filter),
                                                     done=True, unbroken=True)
                            ew.write_event(event)
                            write_count += 1
                            if not write_count % 2000:
                                helper.log_info(
                                    f"[TrendMicro OAT] <{cid}> {write_count} events has been written")
                    if write_count % 2000:
                        helper.log_info(
                            f"[TrendMicro OAT] <{cid}> {write_count} events has been written")
                    helper.log_info(
                        "[TrendMicro OAT] <%s> get totalCount: %d" % (cid, write_count))
                if next_link:
                    query_params["pageToken"] = utils.query_params_parse(next_link)["pageToken"]
                else:
                    break

            checkpoint_time = end_time
            package_bucket = curr_bucket

    except requests.exceptions.Timeout as e:
        helper.log_error(
            "[TrendMicro OAT] <%s> oat request timeout error: %s" % (cid, repr(e)))

        if utils.isotime_delta(startTime, nowTime, ft_str) >= 60*60*24*7:
            checkpoint_time = utils.format_iso_time(ft_str)

        return 1
    except requests.exceptions.HTTPError as e:
        helper.log_error("[TrendMicro OAT] <%s> oat request error: %s %s" % (
            cid, repr(e), str(endpoint)))

        if utils.isotime_delta(startTime, nowTime, ft_str) >= 60*60*24*7:
            checkpoint_time = utils.format_iso_time(ft_str)

        return 1
    except Exception as e:
        helper.log_error(
            "[TrendMicro OAT] <%s> oat exception: %s" % (cid, repr(e)))
        return 1
    finally:
        utils.update_context(STANZA, cid, 'startTime', checkpoint_time)
    helper.log_info(f"[TrendMicro OAT] <{cid}> events writing completed")
    return 0


def collect_events(helper, ew):
    endpoint = helper.get_arg('global_account')['endpoint']
    tokens = helper.get_arg('global_account')['token']
    if (not endpoint) or (not tokens):
        helper.log_info("[TrendMicro OAT] no valid config, will pass")
        return 0
    tokens = utils.split_token(tokens)
    return_status = 0
    for token in tokens:
        return_status = return_status | collect_events_for_one_consumer(
            helper, ew, endpoint, token)
    utils.update_context("GLOBAL", None, 'oatSettingModify', 0)
    return return_status


class OATDataPipeline:
    ctx_name = "Observed_Attack_Techniques_Pipeline"

    def __init__(
        self,
        helper,
        endpoint,
        token,
        proxies,
        risk_level,
        cid
    ) -> None:
        self.__helper = helper
        self.__endpoint = endpoint
        self.__token = token
        self.__proxies = proxies
        self.__query_levels = format_risk_levels(risk_level)
        if (not self.__endpoint) or (not self.__token):
            raise Exception('no valid config')
        self.__headers = {
            'Authorization': 'Bearer ' + self.__token,
            'Content-Type': 'application/json;charset=utf-8',
            "User-Agent": "TMXDRSplunkAddon/" + str(APP_VERSION)
        }
        self._cid = cid
        self.get_setting()

    def get_setting(self):
        if (not self.__endpoint) or (not self.__token):
            raise Exception('no valid config')
        need_reg = False
        pipe_ctx = utils.fetch_context(self.ctx_name, self._cid)
        uuid = pipe_ctx.get('pipelineId')
        if uuid is not None:
            res = requests.request(
                url=f"{self.__endpoint}{API_PATH}/{uuid}",
                method="GET",
                headers=self.__headers,
                proxies=self.__proxies
            )
            if res.status_code == requests.codes.bad_request:
                need_reg = True
        else:
            need_reg = True
        if need_reg:
            config = {
                "riskLevels": self.__query_levels,
                "hasDetail": True,
                "description": "Trend Vision One for Splunk (XDR)"
            }
            res = requests.request(
                url=self.__endpoint + API_PATH,
                method="POST",
                headers=self.__headers,
                proxies=self.__proxies,
                json=config
            )
            self.__helper.log_info("[TrendMicro OAT] <%s> request regist to oat: %s" % (
                self._cid, json.dumps(config)))
            self.__helper.log_info("[TrendMicro OAT] <%s> x-trace-id: %s, response: %s" %
                                   (self._cid, res.headers.get('x-trace-id'), res.text))
            if res.status_code == requests.codes.created:
                self.__helper.log_info("[TrendMicro OAT] <%s> init register success: %s" % (
                    self._cid, json.dumps(config)))
            else:
                raise Exception("fail to init register")
            location: str = res.headers.get("Location", "")
            uuid = location.split("/")[-1]
            if bool(uuid) == False:
                raise Exception(
                    f"invalid oat pipeline uuid, headers: {json.dumps(dict(res.headers))}")
            utils.update_context(self.ctx_name, self._cid, 'pipelineId', uuid)

            res = requests.request(
                url=f"{self.__endpoint}{API_PATH}/{uuid}",
                method="GET",
                headers=self.__headers,
                proxies=self.__proxies
            )
        res.raise_for_status()
        return res.json()

    def update(self, risk_level=None):
        if (not self.__endpoint) or (not self.__token):
            raise Exception('no valid config')
        if risk_level is not None:
            self.__query_levels = format_risk_levels(risk_level)
        config = {
            "riskLevels": self.__query_levels,
            "hasDetail": True,
        }
        pipe_ctx = utils.fetch_context(self.ctx_name, self._cid)
        uuid = pipe_ctx.get('pipelineId')
        res = requests.request(
            url=f"{self.__endpoint}{API_PATH}/{uuid}",
            method="PATCH",
            headers=self.__headers,
            proxies=self.__proxies,
            json=config
        )
        self.__helper.log_info("[TrendMicro OAT] <%s> request update to oat: %s" % (
            self._cid, json.dumps(config)))
        res.raise_for_status()
        self.__helper.log_info("[TrendMicro OAT] <%s> update register config success: %s" % (
            self._cid, json.dumps(config)))
