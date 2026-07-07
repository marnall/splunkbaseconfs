import logging
import os
import json
from logging.handlers import RotatingFileHandler

import splunk.rest


'''
Rest Endpoint URLS

'''
resource = {
    'ACTIVE': '/api/location/v2/clients/',
    'MAP': '/api/config/v1/maps',
    'ANALYTICS': '/api/analytics/v1/summary',
    'FLOORLIST': '/api/config/v1/maps/floor/list',
    'FLOORWISE': '/api/config/v1/maps/info/'
}


def get_logger(logger_id):
    splunk_home = os.environ['SPLUNK_HOME']
    log_path = splunk_home + '/var/log/TA-CMX'

    maxbytes = 2000000

    if not (os.path.isdir(log_path)):
        os.makedirs(log_path)

    handler = RotatingFileHandler(log_path + '/tacmx.log', maxBytes = maxbytes, backupCount = 20)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger = logging.getLogger(logger_id)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


def get_credentials(session_key):
    r = splunk.rest.simpleRequest("/servicesNS/nobody/TA-CMX/storage/passwords?search=TA-CMX&output_mode=json",
                                  session_key, method = 'GET')
    username = ""
    password = ""
    logger = get_logger("CMXUTIL")

    if 200 <= int(r[0]["status"]) <= 300:
        result_storage_password = json.loads(r[1])
        if len(result_storage_password["entry"]) > 0:
            for ele in result_storage_password["entry"]:

                if ele["content"]["realm"] == "TA-CMX":
                    password = ele["content"]["clear_password"]
                    username = ele["content"]["username"]
                    break
    return username, password


def get_hec_credentials(session_key):
    r = splunk.rest.simpleRequest("/servicesNS/nobody/TA-CMX/storage/passwords?search=TA-CMX&output_mode=json",
                                  session_key, method = 'GET')
    username = ""
    password = ""

    if 200 <= int(r[0]["status"]) <= 300:
        result_storage_password = json.loads(r[1])
        if len(result_storage_password["entry"]) > 0:
            for ele in result_storage_password["entry"]:

                if ele["content"]["realm"] == "TA-CMX-HEC":
                    password = ele["content"]["clear_password"]
                    username = ele["content"]["username"]
                    break
    return password


'''
    To read configurations from cmxsetup.conf file
'''


def get_cmx_conf(session_key):
    r = splunk.rest.simpleRequest(
        "/services/cmx/cmxcustomendpoint?output_mode=json", session_key, method = 'GET')

    conf_dict = {}
    result = json.loads(r[1])
    if 200 <= int(r[0]["status"]) <= 300:
        conf_dict = result["entry"][0]["content"]

    return conf_dict


def enable_ssl_for_http(session_key):
    r = splunk.rest.simpleRequest(
        "/servicesNS/admin/splunk_httpinput/data/inputs/http/http?output_mode=json", session_key, method = 'GET')

    result = json.loads(r[1])
    if 200 <= int(r[0]["status"]) <= 300:
        conf_dict = result["entry"][0]["content"]

        if conf_dict["enableSSL"] == "False":
            post_args = {
                "enableSSL": 1,
            }
            r = splunk.rest.simpleRequest("/servicesNS/admin/splunk_httpinput/data/inputs/http/http/", session_key,
                                          postargs = post_args, method = 'POST')

    return r