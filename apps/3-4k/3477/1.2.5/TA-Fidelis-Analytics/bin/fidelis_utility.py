import logging
import os
from logging.handlers import RotatingFileHandler
import json

import splunk.entity as entity
import splunk.rest

#REST URL for Fidelis Cyber Security
resource ={
  'login' : '/j/login.html',
  'selection_values': '/j/rest/v1/alert/selection_values/',

}

def get_credentials(session_key, logger_key):
    logger = get_logger(logger_key)
    myapp = "TA-Fidelis-Analytics"
    try:
        # list all credentials
        entities = entity.getEntities(['admin', 'passwords'], search = myapp, namespace = myapp, owner = 'nobody',
                                      sessionKey = session_key)
    except Exception as e:
        logger.error("TA Fidelis Error: Could not get %s credentials from splunk : %s" % (myapp, str(e)))

    # return first set of credentials
    username = ""
    password = ""
    fidelis_credentials = dict()
    for key, value in entities.items():
        if (str(value['eai:acl']['app'])) == myapp:
            fidelis_key = str(key.split(':')[0]).strip()
            username = value['username']
            password = value['clear_password']
            credential = [username, password]
            fidelis_credentials[fidelis_key] = list(credential)
    return password, username


def get_logger(logger_id):
    splunk_home = os.environ['SPLUNK_HOME']
    log_path = splunk_home + '/var/log/TA-Fidelis-Analytics/'

    maxbytes = 2000000

    if not (os.path.isdir(log_path)):
        os.makedirs(log_path)

    handler = RotatingFileHandler(log_path + '/fidelis.log', maxBytes = maxbytes, backupCount = 20)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger = logging.getLogger(logger_id)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


def get_fidelis_conf(session_key):
    r = splunk.rest.simpleRequest(
        "/services/fidelis/fideliscustomendpoint?output_mode=json", session_key, method = 'GET')

    conf_dict = {}
    result = json.loads(r[1])
    if 200 <= int(r[0]["status"]) <= 300:
        conf_dict = result["entry"][0]["content"]

    return conf_dict

def is_app_configured(session_key,app_name):

    configured=False
    r = splunk.rest.simpleRequest(
        "/servicesNS/nobody/system/apps/local/TA-Fidelis-Analytics?output_mode=json", session_key, method = 'GET')

    conf_dict = {}
    result = json.loads(r[1])

    if 200 <= int(r[0]["status"]) <= 300:
        configured = result["entry"][0]["content"]["configured"]

    return configured