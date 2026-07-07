import io
import json
import logging
import os
import re
import sys
import traceback
from datetime import datetime, timedelta

import pytz
import requests
import splunk.Intersplunk as view
import splunk.clilib.cli_common as cli_lib

import sn_sec_util as sn_util
import sn_tokens
import splunklib.client as client
import splunklib.results as results
from solnlib import conf_manager

utc = pytz.UTC


def setup_logger():
    access_settings = cli_lib.getMergedConf("sn_sec_instance")
    level = access_settings['splunk_log']['logLevel']
    log_file_name = "EI_ServiceNow_SecOps"
    logger = logging.getLogger(log_file_name)
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(
        os.environ['SPLUNK_HOME'] + '/var/log/splunk/' + log_file_name + '.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


logger = setup_logger()
logger.debug("checking log hit in event ingest file")

DEFAULT_ENDPOINT = "/api/sn_sec_splunk_v2/event_ingestion"


def get_auth_token(stdin_data):
    try:
        return stdin_data[stdin_data.find("<authToken>") + 11:stdin_data.find("</authToken>")]
    except Exception:
        view.parseError(traceback.format_exc())
        return ""


def get_url(settings):
    endpoint = DEFAULT_ENDPOINT
    if "endpoint" in settings and settings["endpoint"]:
        endpoint = settings["endpoint"]

    return "{0}{1}".format(settings['url'], endpoint)


def get_proxies(settings):
    url = settings['proxy_url'].strip()
    user = settings['proxy_username']
    port = settings['proxy_port']
    pwd = settings['proxy_password']

    if "://" not in url:
        url = "https://{0}".format(url)
    if port:
        url = "{0}:{1}".format(url, port)
    if user and pwd:
        url = url.replace("://", "://{0}:{1}@".format(user, pwd))
    return {"http": url, "https": url}


def get_instance(argv):
    try:
        return argv[1]
    except Exception:
        view.parseError(traceback.format_exc())
    return ""


def get_sid(argv):
    try:
        return argv[2]
    except Exception:
        view.parseError(traceback.format_exc())
    return ""


def get_offset(argv):
    try:
        return argv[3]
    except Exception:
        view.parseError(traceback.format_exc())
    return ""


def get_source(argv):
    try:
        return argv[4]
    except Exception:
        view.parseError(traceback.format_exc())
    return ""


def get_event(session_key, sid, offset):
    try:
        service = client.connect(token=session_key, app=sn_util.getAppName())
        stream = service.job(sid).results(count="1", offset=offset)

        out = io.BytesIO()
        out.write(stream.read())

        # extract the raw xml of the event and store in a seekable buffer
        event = {}
        resp = out.getvalue().decode("utf-8")
        event["xml"] = re.sub(r"\s+", " ", resp)
        out.seek(0)

        # will only be 1 result
        reader = results.ResultsReader(out)
        for fields in reader:
            fields["sid"] = sid
            break
        event["fields"] = fields

        return event
    except Exception as exception:
        logging.error(traceback.format_exc())
        view.parseError(exception)
    return None


def store_new_access_token_in_config_file(session_key, new_access_token, refresh_token, expiry_time, client_secret, realm):
    logger.debug("Invoking function : store_new_access_token_in_config_file")
    dt = datetime.now() + timedelta(seconds=expiry_time)
    dt = dt.replace(tzinfo=utc)
    token_expiry_time = datetime.strftime(dt, '%m-%d-%y %H:%M:%S')
    cfm = conf_manager.ConfManager(session_key, sn_tokens.APP_NAME)
    cfm_inputs_conf = cfm.get_conf("sn_sec_instance")
    logger.debug("reading information from configuration file for storing newly generated access token")
    inputs_conf_obj = cfm_inputs_conf.get_all()
    logger.debug("read information from configuration file properly for storing token")
    input_items = list(inputs_conf_obj.items())
    if input_items:
        for input_stanza, input_info in input_items:
            if input_stanza == realm:
                if "proxy_password" in input_info:
                    cfm_inputs_conf.update(input_stanza,
                                           {"access_token": new_access_token, "refresh_token": refresh_token,
                                            "clientSecret": client_secret, "expiry_time": token_expiry_time,
                                            "proxy_password": input_info["proxy_password"]},
                                           ['access_token', 'refresh_token', 'clientSecret', 'proxy_password'])
                else:
                    cfm_inputs_conf.update(input_stanza,
                                           {"access_token": new_access_token, "refresh_token": refresh_token,
                                            "clientSecret": client_secret, "expiry_time": token_expiry_time},
                                           ['access_token', 'refresh_token', 'clientSecret'])
                logger.debug("updated configuration file successfully with new access token with encryption !!")


def handle_response(session_key, status_code, url, record_name):
    is_success = False
    error_reason = ""
    if 300 > status_code >= 200:
        is_success = True
    if status_code == 400:
        error_reason = ":Bad request"
    if status_code == 401:
        error_reason = ":Unauthorized"
    if status_code == 403:
        error_reason = ":Forbidden"
    if status_code == 404:
        error_reason = ":Not found"
    if status_code == 405:
        error_reason = ":Method not allowed"
    # Provide error message
    if not is_success:
        error_text = "ERROR Unable to create %s, response code %d %s via REST call to %s" % (
            record_name, status_code, error_reason, url)
        view.parseError(error_text)
    return is_success


def generate_new_access_token(access_settings):
    logger.debug("generating new access token using refresh token")
    client_id = access_settings.get("clientId")  # accessSettings['sn_instance']['clientId']
    client_secret = access_settings.get("clientSecret")  # accessSettings['sn_instance']['clientSecret']
    url = access_settings.get("url") + "oauth_token.do"  # accessSettings['sn_instance']['url'] + "oauth_token.do"
    refresh_token = access_settings.get("refresh_token")  # accessSettings['sn_instance']['refresh_token']
    payload = 'grant_type=refresh_token&client_id=' + client_id + '&client_secret=' + client_secret + \
              '&refresh_token=' + refresh_token
    proxies = {}
    if 'proxy_url' in access_settings and access_settings['proxy_url']:
        proxies = get_proxies(access_settings)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    try:
        response = requests.request("POST", url, headers=headers, proxies=proxies, data=payload)
    except Exception as exception:
        logger.error(exception)
        response = {'status_code': 500, 'content': {'error_description': 'Internal Server Error'}}
    content = json.loads(response.content)
    if response.status_code == 200:
        logger.debug("new access token generated successfully !!")
        return {'status_code': 200, 'access_token': content["access_token"], 'refresh_token': refresh_token,
                'expiry_time': content["expires_in"]}
    else:
        logger.error("failed to generate new access token !!")
        return {'status_code': response.status_code, 'url': url, 'error': 'access denied'}


def post_to_servicenow_using_token(access_settings, data_values, session_key, event_incident_endpoint, realm):
    cfm = conf_manager.ConfManager(session_key, sn_tokens.APP_NAME)
    cfm_inputs_conf = cfm.get_conf("sn_sec_instance")
    logger.debug("Reading configuration file for creating incident")
    try:
        inputs_conf_obj = cfm_inputs_conf.get_all()
    except Exception as exception:
        view.parseError("Error in reading config")
        logger.error(exception)
    if realm in inputs_conf_obj:
        access_settings = inputs_conf_obj[realm]
    expiry_time = datetime.strptime(access_settings.get("expiry_time"), '%m-%d-%y %H:%M:%S')
    current_time = datetime.now()
    continue_flag = True
    access_token = access_settings.get("access_token")
    logger.debug("checking expiry time of access token")
    if expiry_time < current_time:
        logger.debug("access token expired !!")
        response = generate_new_access_token(access_settings)
        if response["status_code"] == 200:
            access_token = response["access_token"]
            logger.debug("storing and encrypting newly generated access token in configuration file")
            store_new_access_token_in_config_file(session_key, response["access_token"], response["refresh_token"],
                                                  response["expiry_time"], access_settings.get("clientSecret"), realm)
        else:
            continue_flag = False
            logger.error("failed : while generating access token using refresh token")
            logger.debug("Refresh token expired !!")
            handle_response(session_key, response.get('status_code'), response.get('url'), "security incident")
    else:
        logger.debug("access token not expired !!")

    if continue_flag:
        url = access_settings.get("url") + event_incident_endpoint
        proxies = {}
        if access_settings['proxy_url']:
            proxies = get_proxies(access_settings)

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + access_token
        }
        logger.debug("Request data for event : {0}".format(data_values))
        try:
            response = requests.request("POST", url, headers=headers, proxies=proxies, data=data_values)
        except Exception as exception:
            logger.error(exception)
            response = {'status_code': 500, 'content': {'error_description': 'Internal Server Error'}}
        logger.debug("Response : " + response.text)

        if response.status_code == 201:
            logger.info("Created record succesfully")
        else:
            logger.info("failed to create record")

        handle_response(session_key, response.status_code, url, "security incident")


def post_to_servicenow(session_key, **kwargs):
    logger.debug("Invoking post_to_servicenow")
    try:
        realm = kwargs["realm"]
        instance_conf = cli_lib.getMergedConf("sn_sec_instance")
        auth_type = instance_conf[realm]['auth_type']
        settings = instance_conf[realm]
        data = json.dumps({
            "source": kwargs["source"],
            "fields": kwargs["fields"],
            "xml": kwargs["xml"],
        })
        if not settings:
            view.parseError("No sn_instance in config")
            return

        if auth_type == "OAuth":
            logger.info("Creating Incident Using OAuth")
            post_to_servicenow_using_token(instance_conf, data, session_key, DEFAULT_ENDPOINT, realm)
        else:
            logger.debug("Invoking els epart")
            pwd, settings['proxy_password'] = sn_util.getCredentials(session_key, realm)

            user = settings['username']
            proxies = {}
            if 'proxy_url' in settings and settings['proxy_url']:
                proxies = get_proxies(settings)

            url = get_url(settings)

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            logger.debug("Request data for event : {0}".format(data))
            response = requests.request("POST", url, headers=headers, auth=(user, pwd), proxies=proxies, data=data)
            logger.debug("Response status code while creating record: " + str(response.status_code))

            if response.status_code != requests.codes.created:
                body = json.loads(response.text)["result"]["error"]
                logging.error("" + str(response.status_code) + " " + body)
                view.parseError("Unsuccessful api response from instance")
    except Exception as exception:
        logging.error(traceback.format_exc())
        view.parseError("Unable to forward notable event")


def main():
    try:
        stdin_data = sys.stdin.read()
        session_key = get_auth_token(stdin_data)

        sid = get_sid(sys.argv)
        offset = get_offset(sys.argv)
        source = get_source(sys.argv)
        realm = sn_util.getRealm(get_instance(sys.argv))

        event = get_event(session_key, sid, offset)
        if event:
            post_to_servicenow(session_key, source=source, realm=realm, fields=event["fields"], xml=event["xml"])
    except Exception as exception:
        logging.error(traceback.format_exc())
        view.parseError(exception)


main()
