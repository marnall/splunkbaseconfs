import requests
import time

from scorecard_exceptions import InvalidAPIKeyError, ResourceNotFoundError, InvalidJSONError, ServerError
from config import SS_RATE_LIMIT


API_HIT_COUNT = 0
INVALID_JSON_ERROR_MSG = "URL: {}\nparams: {}\nstatus code: {}\nContent: {}"
STATUS_FORCELIST = list(range(500, 600)) + [429,]


def get_json_from_url(url, headers=None, params=None, proxy=None, helper=None):
    """Creates json response from url.

    :param url: str, url to call
    :param headers: dict, Optional custom headers
    :param params: dict, url parameters
    :param proxy: dict
    :return: object, json data from api mapped to equivalent python objects
    """
    headers = headers or {}
    params = params or {}
    global API_HIT_COUNT
    API_HIT_COUNT += 1
    if API_HIT_COUNT <= SS_RATE_LIMIT:
        try:
            req = helper.send_http_request(url=url, method='GET', headers=headers,
                                           use_proxy=bool(proxy), parameters=params, verify=True)
        except requests.exceptions.ProxyError as e:
            raise requests.exceptions.ProxyError("Error in connecting to {}\n{}".format(url, str(e)))

        try:
            rv = req.json()
        except ValueError:
            raise InvalidJSONError(INVALID_JSON_ERROR_MSG.format(
                url,
                params,
                req.status_code,
                req.content
            ))

        if req.status_code == 401:
            raise InvalidAPIKeyError(INVALID_JSON_ERROR_MSG.format(
                url,
                params,
                req.status_code,
                req.content
            ))

        if req.status_code == 404:
            raise ResourceNotFoundError(INVALID_JSON_ERROR_MSG.format(
                url,
                params,
                req.status_code,
                req.content
            ))

        if req.status_code in STATUS_FORCELIST:
            raise ServerError(INVALID_JSON_ERROR_MSG.format(
                url,
                params,
                req.status_code,
                req.content
            ))

        if req.status_code != 200:
            raise requests.RequestException("URL: {} Received status {} with content {}.\n Params {}".format(
                url, req.status_code, req.content, params))
        return rv
    else:
        time.sleep(3600)
        API_HIT_COUNT = 0
        get_json_from_url(url, headers, params, helper)


def connect_to_ss(url, token, params=None, proxy=None, helper=None):
    """Connect to ss api and returns json data.

    :param url: str
    :param token: str
    :param params: dict, url parameters
    :param proxy: dict
    :return: json
    """
    headers = {
        'authorization': 'Token {}'.format(token),
        'X-SSC-Application-Name': 'Splunk',
        'X-SSC-Application-Version': '2.3.4',
    }
    rv = get_json_from_url(url, headers, params, proxy, helper)
    return rv


def get_value_from_dict_list(iterable, key, value):
    """Checks the key exists and matches with the value in a iterable of dicts, and returns it if present.

    :param iterable:
    :param key: str, Key to check
    :param value: str, value to check
    :return: dict if present else None
    """
    for item in iterable:
        if key in item.keys() and item[key] == value:
            return item

    return None
