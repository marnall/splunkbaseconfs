import sys, os.path

# for import lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

import logging
import logger_manager

logger = logger_manager.setup_logging("search", logging.DEBUG)

import docodoco_advance_utils
import docodoco_advance_req

VALID_ROUTES = {"docodoco", "apihub"}


def checkDict(value):
    check_dict = False
    if isinstance(value, dict):
        check_dict = True
    return check_dict


def checkThirdPartyData(dict_in, target):
    res = ""
    end = False
    for key, value in dict_in.items():
        if end:
            break
        elif checkDict(value):
            if (target in value) & (checkDict(value.get(target)) is False):
                end = True
                res = value.get(target)
        else:
            res = checkThirdPartyData(value, target)

    return res


def getThirdPartyData(dict_in, target, t_name):
    res = ""
    if t_name in dict_in:
        v = dict_in.get(t_name)
        if (target in v) & (checkDict(v.get(target)) is False):
            res = v.get(target)
        else:
            res = checkThirdPartyData(v, target)

    return res


def getWeatherData(dict_in, target, wtype):
    res = ""
    if wtype == "WeatherA":
        res = dict_in["Area"][target]

    if wtype == "WeatherP":
        res = dict_in["Point"][target]

    return res


def get_api_conn_info(search_command):
    # route に応じて API 接続仕様を返す
    #   - docodoco: client_id (必須) + api_key (必須) + 接続情報
    #   - apihub: x_sbiapi_key (必須) + 接続情報
    #   - 未定義のパラメータまたは無効な必須値があれば ValueError を投げる
    utils = docodoco_advance_utils
    confs = search_command.service.confs
    common = confs[utils.CONF_FILE][utils.CONF_STANZA]

    # route
    route = getattr(common, "route", None)
    if route not in VALID_ROUTES:
        raise ValueError(f"invalid route: {route!r}")
    
    # timeout_sec
    ts = getattr(common, "timeout_sec", None)
    ts = int(ts) if ts not in (None, "") else None
    
    # config parameters
    cview = confs[utils.CONF_FILE][route]

    # secrets
    secrets = search_command.service.storage_passwords

    if route == "docodoco":
        try:
            api_key = next(
                s for s in secrets
                if (s.realm == utils.APP_NAME and s.username == utils.DOCODOCO_API_KEY_IN_PASSWORD_STORE)
            ).clear_password
        except StopIteration:
            api_key = None

        if not api_key:
            raise ValueError("Missing authentication information for Docodoco API: api_key")

        spec = {
            "route": "docodoco",
            "base_url": getattr(cview, "base_url", None),
            "endpoint_path": getattr(cview, "endpoint_path", None),
            "http_method": getattr(common, "http_method", None),
            "param_ip_key": getattr(cview, "param_ip_key", None),
            "client_id_param_key": getattr(cview, "client_id_param_key", None),
            "format_param_key": getattr(cview, "format_param_key", None),
            "format_param_value": getattr(cview, "format_param_value", None),
            "headers": {"Authorization": api_key},
            "client_id": getattr(common, "client_id", None),
            "timeout_sec": ts,
        }
        return spec
    
    # route == "apihub"
    try:
        x_sbiapi_key = next(
            s for s in secrets
            if (s.realm == utils.APP_NAME and s.username == utils.X_SBIAPI_KEY_IN_PASSWORD_STORE)
        ).clear_password
    except StopIteration:
        x_sbiapi_key = None
    
    if not x_sbiapi_key:
        raise ValueError("Missing authentication information for APIHub: x_sbiapi_key")
    
    spec = {
        "route": "apihub",
        "base_url": getattr(cview, "base_url", None),
        "path_template": getattr(cview, "path_template", None),
        "service_id": getattr(cview, "service_id", None),
        "resource": getattr(cview, "resource", None),
        "version": getattr(cview, "version", None),
        "last_segment": getattr(cview, "last_segment", None),
        "http_method": getattr(common, "http_method", None),
        "param_ip_key": getattr(cview, "param_ip_key", None),
        "headers": {
            "X-Sbiapi-User-Appkey": x_sbiapi_key,
            "X-SBIAPI-Host": getattr(cview, "x_sbiapi_host", None),
        },
        "timeout_sec": ts,
    }
    return spec


@Configuration()
class DocoDocoAdvanceCommand(StreamingCommand):
    ipfield = Option(
        doc=""" **Syntax:** **ipfield=***<fieldname>*
        **Description:** Name of the field that will hold the computed
        sum""",
        require=True,
        validate=validators.Fieldname(),
    )

    reqpool = None

    """ Reverse the string.
    """

    def stream(self, records):
        if self.reqpool is None:
            logger.info("new DocoDoco Request Pool")
            conn_info = get_api_conn_info(self)
            self.reqpool = docodoco_advance_req.DocoDocoAdvanceReqPool(conn_info)

        local_records = []
        ip_list = []
        index = 0
        while True:
            try:
                record = records.__next__()
                local_records.append(record)
                ip_list.append(record.get(self.ipfield))
                index += 1
                if index >= 100:
                    # 100件ずつ処理する
                    docodoco_results = self.reqpool.reqDocodocoW(ip_list)
                    yield from self.transformRecords(local_records, docodoco_results)
                    local_records = []
                    ip_list = []
                    index = 0
            except StopIteration:
                if index > 0:
                    # records空の読み取りが終わり、残りのレコードがある場合は残りを処理する
                    docodoco_results = self.reqpool.reqDocodocoW(ip_list)
                    yield from self.transformRecords(local_records, docodoco_results)
                break

    def transformRecords(self, original_records, docodoco_results):
        for index, record in enumerate(original_records):
            result = docodoco_results[index]  # cause results.pop(0) is very slow.

            req_error = False
            req_status = result.get("status")

            if req_status == "error":
                req_error = True

            for header_name in docodoco_advance_utils.DOCODOCO_REST_RESPONSE_HEADERS:
                if req_error:
                    record[header_name] = "request failed"
                elif "@" in header_name:
                    target = header_name.split("@")[0]
                    t_name = header_name.split("@")[1]

                    # if((result.has_key("Weather")) and ( t_name == "WeatherA" or t_name == "WeatherP")):
                    if ("Weather" in result) and (t_name == "WeatherA" or t_name == "WeatherP"):
                        record[header_name] = getWeatherData(result["Weather"], target, t_name)
                    else:
                        record[header_name] = getThirdPartyData(result, target, t_name)
                elif (header_name in result) & (checkDict(result.get(header_name)) is False):
                    record[header_name] = result.get(header_name)
                else:
                    record[header_name] = checkThirdPartyData(result, header_name)

            yield record


dispatch(DocoDocoAdvanceCommand, sys.argv, sys.stdin, sys.stdout, __name__)
