#!/usr/bin/env python
"""
This script integrates with Cyberint's next APIs: "ip_check" and "url_check".

Given a suspicious ip / url, some relevant info is crucial to determine whether
it's malicious or not.
Cyberint collects data from multiple sources, which later on are used for that
purpose among other use cases, and those end-points provide that enrichment.

** In order to use the API properly, a valid token should be configured in a
 config.json file.

Examples:
  - python argos_feeds_api.py --execute '{'query': 'http://some_uel'}': Ask
  for url enrichment to given url
  - python argos_feeds_api.py --execute '{'query': '1.1.1.1'}': Ask
  for ip enrichment to given ip
"""

from __future__ import print_function, unicode_literals

import cookielib
import json
import logging
import os
import re
import sys
import time
import urllib2
import urlparse
from httplib import BAD_REQUEST
from logging import handlers
from urllib2 import HTTPError

__description__ = 'Argos API for ip_check and url_check'
__version__ = '1.0.5'
__author__ = 'Aaron Abaev'

RESPONSE_FILE_TEMPLATE = 'stash_cyberint_response_{}.json'
LOG_FILE_TEMPLATE = 'cyberint_{}.log'
USE_LOGS = False
LOGLEVEL = logging.DEBUG

CONFIG_PATH = os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", "cyberint_argos", "local")
CONFIG_FILE = os.path.join(CONFIG_PATH, "config.conf")
CONFIG_SPLITTER = '='

DEFAULT_OUTPUT_DIR = '/tmp'
OUTPUT_PATH = ('var', 'spool')

HEADERS = {'Content-Type': 'application/json'}

# ipv4 regex
octet_regex = r'(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9][0-9]|[0-9])'
BASE_REGEX = r'^((%s\.){3}%s)$' % (octet_regex, octet_regex)
IPV4_REGEX = re.compile(BASE_REGEX, flags=re.UNICODE)

URL_PATTERN = '{url}/api/v1/{endpoint}'
IP_CHECK_ENDPOINT = 'ip_check'
URL_CHECK_ENDPOINT = 'url_check'

logger = logging.getLogger()
CONFIG_PARAMS = {}


def _read_config_params():
    def _clean_lines(line):
        s_line = str(line).strip()
        return not (s_line.startswith('[') and s_line.endswith(']'))

    global CONFIG_PARAMS
    with open(CONFIG_FILE) as config_file:
        for line in filter(_clean_lines, config_file.readlines()):
            param = line.split(CONFIG_SPLITTER)
            CONFIG_PARAMS[param[0].strip()] = param[1].strip()


def _create_log_name():
    return LOG_FILE_TEMPLATE.format(time.strftime('%b-%d-%Y_%H%M',
                                                  time.localtime()))


def create_logger():
    log_file = os.path.join(_get_dir('logs'), _create_log_name())

    file_handler = handlers.RotatingFileHandler(
        log_file, maxBytes=25000000, backupCount=5)
    file_handler.setLevel(LOGLEVEL)

    logger.addHandler(file_handler)
    logger.setLevel(LOGLEVEL)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def call_argos_endpoint(endpoint, post_params, token):
    logger.debug('calling argos api', extra={'endpoint': endpoint,
                                             'post_params': post_params})
    domain = urlparse.urlparse(endpoint).hostname
    cookiejar = create_cookie(token, domain)
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookiejar))

    request = urllib2.Request(endpoint, post_params, HEADERS)
    response = opener.open(request)
    return json.loads(response.read().decode('utf8'))


def create_cookie(token, domain):
    cookiejar = cookielib.CookieJar()
    cookiejar.clear_session_cookies()
    cookie = cookielib.Cookie(
        0, 'access_token', token, None, False, domain,
        False, False, '/', True, False, None, True,
        None, None, {'HttpOnly': None})
    cookiejar.set_cookie(cookie)
    return cookiejar


def is_ipv4(ip):
    return bool(IPV4_REGEX.match(ip))


def is_full_url(url, supported_schemes=('http', 'https')):
    try:
        parsed_url = urlparse.urlparse(url)
        if parsed_url.scheme not in supported_schemes:
            return False
    except ValueError:
        return False
    return True


def create_error_resp(msg, status=None):
    logger.error('Error response: %s', msg)
    return {
        'error': True, 'message': '%s' % msg,
        'response': [], 'status': status
    }


def get_argos_resp(endpoint, json_data):
    post_params = json.dumps(json_data)

    try:
        argos_url = CONFIG_PARAMS['argos_url']
        full_url = URL_PATTERN.format(url=argos_url, endpoint=endpoint)
        return call_argos_endpoint(full_url, post_params, CONFIG_PARAMS['token'])  # noqa
    except HTTPError as err:
        logger.exception('Error calling api')
        return create_error_resp(err.message, err.code)
    except Exception as err:
        logger.exception('Unknown error occurred')
        return create_error_resp(err.message)


def _ip_check(ip):
    logger.debug('ip_check, ip: %s', ip)
    return get_argos_resp(IP_CHECK_ENDPOINT, {'ip': ip})


def _url_check(url):
    logger.debug('url_check, url: %s', url)
    return get_argos_resp(URL_CHECK_ENDPOINT, {'url': url})


def handle_query(query):
    """
    Classify given 'query' to supported types and call relevant API.
    Supported 'query' string is IPv4 or a valid url
    :param str query:
    :raises ValueError
    :return:
    """
    if is_ipv4(query):
        return _ip_check(query)
    if is_full_url(query):
        return _url_check(query)

    return create_error_resp('query: {%s} not supported' % query, BAD_REQUEST)


def parse_params(input_params):
    """
    Parse given input params. Validate relevant fields were given and
    extract query to search for
    :param dict input_params:
    :raises ValueError
    :return: str
    """
    if not input_params:
        raise ValueError('Bad params received: %s', input_params)

    query = input_params.get('configuration', {}).get('query')
    if not query:
        raise ValueError('Bad params received: %s', input_params)

    return query


def _write_response(response):
    response_file = RESPONSE_FILE_TEMPLATE.format(time.strftime('%b-%d-%Y_%H%M',
                                                  time.localtime()))
    response_file = os.path.join(_get_dir('splunk'), response_file)
    with open(response_file, 'w') as output:
        json.dump(response, output)


def _get_dir(dir_name):
    dir_full_path = OUTPUT_PATH + (dir_name,)
    base_dir = os.environ.get('SPLUNK_HOME') or DEFAULT_OUTPUT_DIR
    req_dir = os.path.join(base_dir, *dir_full_path)

    if not os.path.exists(req_dir):
        os.makedirs(req_dir)

    return req_dir


def main():
    _read_config_params()
    if USE_LOGS:
        create_logger()

    if not (len(sys.argv) > 1 and sys.argv[1] == '--execute'):
        return create_error_resp('Bad params received: %s' % sys.argv,
                                 BAD_REQUEST)
    try:
        stdin_rec = sys.stdin.read().strip()
        logger.debug('input received: %s', stdin_rec)
        params = json.loads(stdin_rec)
        search_query = parse_params(params)
    except ValueError as val_err:
        return create_error_resp(val_err.message, BAD_REQUEST)

    resp = handle_query(search_query)
    logger.info('response: %s', resp)
    _write_response(resp['response'])

    return resp


if __name__ == '__main__':
    main()
