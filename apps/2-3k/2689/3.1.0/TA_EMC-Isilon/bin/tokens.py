# define token functions for substitution in endpoint URL
# /someurl/foo/$sometoken$/goo -> /someurl/foo/zoo/goo

# functions can return a scalar or a list
# if a scalar is returned , then a single URL request will be made
# if a list is returned , then (n) URL requests will be made , where (n) is the
# length of the list
# multiple requests will get executed in parallel threads

from builtins import str
from builtins import range
import datetime
import traceback
import json
import re
from pytz import timezone
import responsehandlers
import isilon_utilities as utilities
import const


# This method is no longer required as it is in use for endpoints for version below 7.
# Keeping it for the safer side - for the consistency.


def _get_count_from_endpoint(path, cookie, proxy, req_args, node):
    """Returns the count from the endpoint."""
    csrf = cookie.get("isicsrf")
    sessid = cookie.get("isisessid")
    session = utilities.retry_session()
    if csrf:
        headers = {
            "X-CSRF-Token": str(csrf),
            "Cookie": "isisessid=" + str(sessid),
            "Referer": "https://" + str(node) + ":" + const.ISILON_PORT,
        }
        response = session.get(path, headers=headers, proxies=proxy, **req_args)
    else:
        response = session.get(path, cookies=cookie, proxies=proxy, **req_args)
    response.raise_for_status()
    response_json = json.loads(response.text, object_hook=responsehandlers._decode_dict)
    count = max([stat_rec["value"] for stat_rec in response_json["stats"]])
    return count


# This method is no longer required as it is in use for endpoints for version below 7.
# Keeping it for the safer side - for the consistency.


def get_count(path, cookie, proxy, node, req_args, logger):
    """Returns updated endpoint for count endpoints."""
    try:
        count_endpoint = path.rsplit(".", 2)[0]
        actual_endpoint = path.split("$", 1)[0]
        url_params = path.rsplit("&", 1)[1] if "&" in path else None
        endpoint_list = []
        count_endpoint = count_endpoint + ".count"
        count = _get_count_from_endpoint(count_endpoint, cookie, proxy, req_args, node)
        for y in range(int(count)):
            end_point = actual_endpoint + str(y)
            if url_params is not None:
                end_point = end_point + "&" + url_params
            endpoint_list.append(end_point)
        return endpoint_list
    except Exception:
        logger.error(
            "message=error_while_getting_count | Error occured while getting count for endpoint '{}'.\n{}"
            .format(path, traceback.format_exc())
        )
        return []


def get_version(path, cookie, proxy, req_args, node, logger):
    """Returns the product version."""
    try:
        csrf = cookie.get("isicsrf")
        sessid = cookie.get("isisessid")
        session = utilities.retry_session()
        if csrf:
            headers = {
                "X-CSRF-Token": str(csrf),
                "Cookie": "isisessid=" + str(sessid),
                "Referer": "https://" + str(node) + ":" + const.ISILON_PORT,
            }
            response = session.get(path, headers=headers, proxies=proxy, **req_args)
        else:
            response = session.get(path, cookies=cookie, proxies=proxy, **req_args)
        response_json = json.loads(
            response.text, object_hook=responsehandlers._decode_dict
        )
        version = response_json["onefs_version"]["release"]
        timezone = response_json["timezone"]["path"]
        result = {"version": version, "timezone": timezone}
        logger.debug("message=version_and_timezone_value | Successfully got the version and timezone values.")
        return result
    except Exception:
        logger.error(
            "message=error_while_getting_version | Error occured while getting version from request call.\n{}"
            .format(traceback.format_exc())
        )
        raise


def get_events_from_version(path, cookie, proxy, node, req_args, logger):
    """Updates the endpoint based on the product version."""
    version_check_path = path.split("/platform")[0] + "/platform/1/cluster/config"
    result = get_version(version_check_path, cookie, proxy, req_args, node, logger)
    version = re.findall("[0-9]+", result.get("version"))
    logger.debug("message=version_details | Version is = {}".format(version))
    path = path.split("/platform")[0] + "/platform/3/event/eventlists?begin={TIME}"
    timezone = result.get("timezone", "")
    path = _replace_token_time(path, node, req_args, timezone, logger)
    return [path]


# Replaces {TIME} token with respective value
def _replace_token_time(path, node, req_args, time_zone, logger):
    """Replaces the time in the pos file with respective time zone."""
    logger.debug("message=replacing_token_time | Replacing the token time in pos file.")
    file_data = None
    auth = req_args.get("auth")
    try:
        filename = "last_call_info.pos"
        tzone = _get_timezone(node, auth, time_zone, filename, logger)
        tz = timezone(tzone)
        now = datetime.datetime.now(tz=tz)
        epoch = datetime.datetime(1970, 1, 1, tzinfo=tz)
        ts_now = int((now - epoch).total_seconds())
        file_data = utilities._read_meta_info(filename, logger)
        if file_data != -1:
            if file_data.get("LAST_CALL_TIME") is not None:
                if file_data.get("LAST_CALL_TIME").get(node) is not None:
                    path = path.format(TIME=file_data.get("LAST_CALL_TIME").get(node))
                    file_data["LAST_CALL_TIME"][str(node)] = ts_now
                    utilities._write_meta_info(file_data, filename, logger)
                else:
                    file_data["LAST_CALL_TIME"][str(node)] = ts_now
                    utilities._write_meta_info(file_data, filename, logger)
                    path = path.format(TIME=ts_now)
            else:
                file_data["LAST_CALL_TIME"] = {}
                file_data["LAST_CALL_TIME"][str(node)] = ts_now
                utilities._write_meta_info(file_data, filename, logger)
                path = path.format(TIME=ts_now)
        else:
            file_data = utilities._read_meta_info(filename, logger)
            if file_data == -1:
                file_data = {}
            file_data["LAST_CALL_TIME"] = {}
            file_data["LAST_CALL_TIME"][str(node)] = ts_now
            utilities._write_meta_info(file_data, filename, logger)
            path = path.format(TIME=ts_now)
        logger.debug("message=updated_token_time | Successfully updated the token time for endpoint - '{}'"
                     .format(path))
        return path
    except Exception:
        logger.error("message=error_replacing_time_value | Error occured while replacing time in pos file.\n{}"
                     .format(traceback.format_exc()))
        raise


def _get_timezone(node, auth, time_zone, filename, logger):
    """Get the timezone from node."""
    try:
        logger.debug("message=getting_timezone | Getting timezone from node.")
        tzone = ""
        logger.debug("message=reading_pos_file_for_timezone | Reading pos file for getting timezone.")
        file_data = utilities._read_meta_info(filename, logger)
        if file_data != -1:
            if file_data.get("TZ") is not None:
                if file_data.get("TZ").get(str(node)) is not None:
                    tzone = file_data.get("TZ").get(str(node))
                else:
                    tzone = file_data["TZ"][str(node)] = time_zone
                    utilities._write_meta_info(file_data, filename, logger)
            else:
                file_data["TZ"] = {}
                tzone = file_data["TZ"][str(node)] = time_zone
                utilities._write_meta_info(file_data, filename, logger)
        else:
            logger.debug("message=pos_file_empty | pos file is empty or does not exist.")
            tzone = time_zone
            file_data = {}
            file_data["TZ"] = {}
            file_data["TZ"][str(node)] = tzone
            utilities._write_meta_info(file_data, filename, logger)
        return tzone
    except Exception:
        logger.error("message=timezone_error | Error occured while getting timezone from node '{}'.\n{}"
                     .format(node, traceback.format_exc()))
        raise


def get_ad_domains(path, cookie, proxy, node, req_args, logger):
    """Returns endpoints for Active directory."""
    logger.debug("message=getting_ad_domains_endpoints | Getting endpoints for active directory domains.")
    endpoint_list = []
    try:
        session = utilities.retry_session()
        get_ad_path = path.split("/platform")[0] + "/platform/1/auth/providers/ads"
        csrf = cookie.get("isicsrf")
        sessid = cookie.get("isisessid")
        if csrf:
            headers = {
                "X-CSRF-Token": str(csrf),
                "Cookie": "isisessid=" + str(sessid),
                "Referer": "https://" + str(node) + ":" + const.ISILON_PORT,
            }
            response = session.get(
                get_ad_path, headers=headers, proxies=proxy, **req_args
            )
        else:
            response = session.get(
                get_ad_path, cookies=cookie, proxies=proxy, **req_args
            )
        response_json = json.loads(
            response.text, object_hook=responsehandlers._decode_dict
        )
        for _, value in response_json.items():
            for valuelist in value:
                ad_name = valuelist.get("id")
                endpoint = path.replace("$get_ad_domains$", str(ad_name))
                endpoint_list.append(endpoint)
        logger.debug("message=ad_domains_endpoints | Successfully got the active directory endpoints.")
        return endpoint_list
    except Exception:
        logger.error(
            "message=error_fetching_ad_domains_info |"
            " Error occured while getting list of Active directory domains.\n{}".format(traceback.format_exc())
        )
        return []
