# encoding = utf-8

import os
import sys

import time
import traceback
from threading import Lock
import re
import json
import tokens
import requests
from authhandlers import TokenAuth
from responsehandlers import IsilonResponseHandler, IsilonEventResponseHandler
from isilon_utilities import get_proxy_data
import isilon_logger_manager as log
import const
from dell_lock import JLock
from isilon_utilities import retry_session, get_release_version, get_cookie

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]
lock_here = Lock()
"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    # This example accesses the modular input variable
    # global_account = definition.parameters.get('global_account', None)
    pass


def post_call_requirements(endpoint_string, logger):
    """Returns endpoint and arguments in dictionary form that needs to be passed in POST call."""
    try:
        if "?" in endpoint_string:
            endpoint_split = endpoint_string.split("?")
            endpoint = endpoint_split[0]
            args_string = endpoint_split[1]
            data_dict = {}
            args_string_split = args_string.split("&")
            for args in args_string_split:
                if args.split("=")[1].lower() in ["true", "1"]:
                    data_dict[args.split("=")[0]] = True
                else:
                    data_dict[args.split("=")[0]] = args.split("=")[1]
            if "limit" in data_dict.keys():
                data_dict["limit"] = int(data_dict["limit"])
            return endpoint, data_dict
        else:
            return endpoint_string, None
    except Exception:
        logger.error("message=post_call_error | Error occured while getting requirements for POST call.\n{}"
                     .format(traceback.format_exc()))
        return endpoint_string, None


def requestEndpoint(http_method, endpoint, cookie, req_args, node, proxy, logger):
    """Hits the endpoint and returns the result of it."""
    csrf = cookie.get("isicsrf")
    sessid = cookie.get("isisessid")
    session = retry_session()
    data = None
    if "12/auth/providers/ads" in str(endpoint):
        http_method = "POST"
        endpoint, data = post_call_requirements(endpoint, logger)

    if csrf:
        headers = {
            "X-CSRF-Token": str(csrf),
            "Cookie": "isisessid=" + str(sessid),
            "Referer": "https://" + str(node) + ":" + const.ISILON_PORT,
        }
        logger.debug("message=requesting_endpoint | Sending the request to endpoint.")
        if http_method == "GET":
            r = session.get(endpoint, headers=headers, proxies=proxy, **req_args)
        elif http_method == "POST":
            r = session.post(endpoint, headers=headers, data=json.dumps(data), proxies=proxy, **req_args)
        elif http_method == "PUT":
            r = session.put(endpoint, headers=headers, proxies=proxy, **req_args)
    else:
        if http_method == "GET":
            r = session.get(endpoint, cookies=cookie, proxies=proxy, **req_args)
        elif http_method == "POST":
            r = session.post(endpoint, cookies=cookie, data=json.dumps(data), proxies=proxy, **req_args)
        elif http_method == "PUT":
            r = session.put(endpoint, cookies=cookie, proxies=proxy, **req_args)
    return r


def replace_api_version(endpoint, endpoint_type, product_version, logger):
    """Replaces the API version for the required endpoint."""
    base_version = tuple(const.DYNAMIC_API_VERSION_CONFIGURATION[endpoint_type]["onefs_base_version"].split("."))
    if product_version >= base_version:
        api_version = const.DYNAMIC_API_VERSION_CONFIGURATION[endpoint_type]["API_alternate_version"]
        updated_endpoint = endpoint.replace("<api_version>", api_version)
        logger.debug("message=endpoint_updated | {} Endpoint updated with API version {}."
                     .format(endpoint_type, api_version))
    else:
        api_version = const.DYNAMIC_API_VERSION_CONFIGURATION[endpoint_type]["API_base_version"]
        updated_endpoint = endpoint.replace("<api_version>", api_version)
        logger.debug("message=endpoint_updated | {} Endpoint updated with API version {}."
                     .format(endpoint_type, api_version))
    return updated_endpoint


def replaceTokens(raw_string, cookie, node, req_args, proxy, logger, username, password):
    """Substitutes the tokens for the particular endpoints."""
    if "<api_version>" in str(raw_string):
        endpoint_type = None
        cookies = get_cookie(node, username, password, req_args["verify"], proxy, logger)
        product_version = get_release_version(node, cookies, req_args["verify"], logger, proxy)
        logger.debug("message=product_version details | Product version is = {}".format(product_version))
        try:
            product_version = product_version.strip("v")
            prod_version = tuple(product_version.split("."))
            if "<api_version>/auth/providers/ads" in str(raw_string):
                endpoint_type = "AD"
            elif "<api_version>/quota/quotas" in str(raw_string):
                endpoint_type = "Quotas"
            raw_string = replace_api_version(raw_string, endpoint_type, prod_version, logger)
        except Exception:
            logger.error("message=error_while_replacing_api_version | Error occured while replacing api version.\n{}"
                         .format(traceback.format_exc()))

    endpoints = [raw_string]
    try:
        substitution_tokens = re.findall("\\$(?:\\w+)\\$", str(raw_string))
        if substitution_tokens:
            logger.debug("message=substitute_tokens_found | Substitution tokens found for "
                         "endpoint - '{}'".format(raw_string))
        for token in substitution_tokens:
            endpoints = getattr(tokens, token[1:-1])(raw_string, cookie, proxy, node, req_args, logger)
        return endpoints
    except Exception:
        logger.error(
            "message=error_substituting_tokens | Error occured while substituting tokens for endpoint - {}.\n{}"
            .format(raw_string, traceback.format_exc())
        )
        return []


def handle_output(response_handler_instance, output, type, endpoint, node, ew, helper, index, logger):
    """Calls the response handler for ingesting data into Splunk."""
    try:
        response_handler_instance(output, type, node, endpoint, ew, helper, index, logger)
        sys.stdout.flush()
    except RuntimeError:
        logger.error(
            "message=error_while_handling_response | Error occured while handling the response for endpoint - {}.\n{}"
            .format(endpoint, traceback.format_exc())
        )


def pagination(http_method, endpoint, r, cookie, req_args, node, backoff_time, proxy, logger):
    """Hits the endpoint in case of pagination and returns the result."""
    responses = []
    logger.info("message=pagination_found | Pagination found for endpoint - '{}'".format(endpoint))
    while True:
        try:
            r_json = json.loads(r.text)
            if "resume" in r_json and r_json["resume"]:
                endpoint = endpoint.split("?")[0] + "?" + "resume=" + r_json["resume"]
                r = requestEndpoint(http_method, endpoint, cookie, req_args, node, proxy, logger)
                responses.append(r)
            else:
                break
        except requests.exceptions.Timeout:
            logger.error(
                "message=http_timeout_error | HTTP Request Timeout error for endpoint - {}.\n{}"
                .format(endpoint, traceback.format_exc())
            )
        except Exception:
            logger.error(
                "message=endpoint_request_error | Error occured while performing request for endpoint - {}.\n{}"
                .format(endpoint, traceback.format_exc())
            )
    return responses


def get_responses(http_method, endpoint, cookie, req_args, node, backoff_time, proxy, logger):
    """Returns the list of responses received after hitting the endpoints."""
    responses = []
    response_handler_instance = IsilonResponseHandler()
    if "eventlists" in endpoint:
        response_handler_instance = IsilonEventResponseHandler()
    try:
        r = requestEndpoint(http_method, endpoint, cookie, req_args, node, proxy, logger)
        responses.append(r)
    except requests.exceptions.Timeout:
        logger.error(
            "message=http_timeout_error | HTTP Request Timeout error for endpoint - {}.\n{}"
            .format(endpoint, traceback.format_exc())
        )
    except Exception:
        logger.error(
            "message=endpoint_request_error | Error occured while performing request for endpoint - {}.\n{}"
            .format(endpoint, traceback.format_exc())
        )

    if "auth/providers/ads" in endpoint:
        responses = responses + pagination(
            http_method, endpoint, r, cookie, req_args, node, backoff_time, proxy, logger
        )
    return response_handler_instance, responses


def run(arg_dict, logger):
    """
    Function from where the actual flow starts.

    Gets called after taking all the required parameters from input page.
    """
    with JLock(str(arg_dict["acct_name"]), logger):
        logger.debug("message=trying_to_acquire_lock | Trying to acquire the lock.")
        with lock_here:
            logger.debug("message=lock_acquired | Lock acquired successfully.")
            custom_auth_handler_args = {
                "auth_type": arg_dict["auth_type"],
                "session_key": arg_dict["session_key"],
                "endpoint": arg_dict["original_endpoint"],
                "node": arg_dict["node"],
                "username": arg_dict["username"],
                "password": arg_dict["password"],
                "proxy": arg_dict["proxy"],
                "logger": logger,
            }
            custom_auth_handler_instance = TokenAuth(**custom_auth_handler_args)
            try:
                verify = arg_dict["verify"]
                req_args = {
                    "verify": verify,
                    "timeout": float(arg_dict["request_timeout"]),
                }
                auth = None
                if custom_auth_handler_instance:
                    auth = custom_auth_handler_instance
                if auth:
                    cookie = auth(verify)
                endpoint_list = replaceTokens(
                    arg_dict["original_endpoint"],
                    cookie,
                    arg_dict["node"],
                    req_args,
                    arg_dict["proxy"],
                    logger,
                    arg_dict["username"],
                    arg_dict["password"]
                )

                for endpoint in endpoint_list:
                    response_handler_instance, responses = get_responses(
                        arg_dict["http_method"],
                        endpoint,
                        cookie,
                        req_args,
                        arg_dict["node"],
                        arg_dict["backoff_time"],
                        arg_dict["proxy"],
                        logger,
                    )
                    try:
                        for res in responses:
                            res.raise_for_status()
                            handle_output(
                                response_handler_instance,
                                res.text,
                                arg_dict["response_type"],
                                endpoint,
                                arg_dict["node"],
                                arg_dict["ew"],
                                arg_dict["helper"],
                                arg_dict["index"],
                                logger,
                            )
                    except requests.exceptions.HTTPError:
                        logger.error(
                            "message=http_request_error | HTTP Request error for endpoint {}.\n{}"
                            .format(endpoint, traceback.format_exc())
                        )
                        if res.status_code == 401:
                            logger.info(
                                "message=getting_new_cookie | Got authentication failure error, "
                                "so getting new session cookie for endpoint '{}'".format(traceback.format_exc())
                            )
                            cookie = auth(verify, res.status_code)
                            response_handler_instance, responses = get_responses(
                                arg_dict["http_method"],
                                endpoint,
                                cookie,
                                req_args,
                                arg_dict["node"],
                                arg_dict["backoff_time"],
                                arg_dict["proxy"],
                                logger,
                            )
                            try:
                                for res in responses:
                                    res.raise_for_status()
                                    handle_output(
                                        response_handler_instance,
                                        res.text,
                                        arg_dict["response_type"],
                                        endpoint,
                                        arg_dict["node"],
                                        arg_dict["ew"],
                                        arg_dict["helper"],
                                        arg_dict["index"],
                                        logger,
                                    )
                            except Exception:
                                logger.error("message=error_while_handling_response | "
                                             "Error while handling response.\n{}".format(traceback.format_exc()))
            except RuntimeError:
                logger.error("message=runtime_error | Runtime error occured.\n{}".format(traceback.format_exc()))
                sys.exit(2)
            except Exception:
                logger.error("message=error_occured | An error occured.\n{}".format(traceback.format_exc()))
                sys.exit(2)


def collect_events(helper, ew):
    """Data collection starts from here."""
    account = helper.get_arg("global_account")
    acct_name = account.get("name")
    username = account.get("username")
    password = account.get("password")
    endpoint = helper.get_arg("endpoint")
    index = helper.get_arg("index")
    inp_name = helper.get_arg("name")
    session_key = helper.context_meta["session_key"]

    original_endpoint = (
        "https://"
        + str(account.get("ip_address"))
        + ":"
        + const.ISILON_PORT
        + str(endpoint)
    )
    node = str(account.get("ip_address"))
    logger = log.setup_logging("ta_emc_isilon_isilon", input_name=inp_name)
    arg_dict = {
        "original_endpoint": original_endpoint,
        "auth_type": const.AUTH_TYPE,
        "session_key": session_key,
        "node": node,
        "username": username,
        "password": password,
        "request_timeout": const.REQUEST_TIMEOUT,
        "backoff_time": const.BACKOFF_TIME,
        "ew": ew,
        "helper": helper,
        "http_method": const.HTTP_METHOD,
        "response_type": const.RESPONSE_TYPE,
        "acct_name": acct_name,
        "index": index,
        "verify": const.VERIFY_SSL,
        "proxy": get_proxy_data(session_key, APP_NAME, logger),
    }

    logger.info("message=data_collection_info | Data Collection Started for endpoint - '{}'.".format(endpoint))
    start_time = time.time()
    run(arg_dict, logger=logger)
    end_time = time.time()
    logger.info("message=data_collection_info | Data Collection Completed.")
    logger.info("message=time_elapsed_for_data_collection | Time taken for data collection = {}"
                .format(end_time - start_time))
