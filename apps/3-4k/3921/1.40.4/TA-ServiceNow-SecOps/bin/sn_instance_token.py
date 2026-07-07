import json
import logging
import logging.handlers
import os
from datetime import datetime, timedelta

import pytz
import requests
import splunk.admin as admin
import splunk.clilib.cli_common as cliLib

import sn_sec_util as snutil
from solnlib import conf_manager

utc = pytz.UTC


def setup_logger():
    accessSettings = cliLib.getMergedConf("sn_sec_instance")
    level = accessSettings['sn_instance']['log_level']
    logFileName = "TA_ServiceNow_SecOps"
    logger = logging.getLogger(logFileName)
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(
        os.environ['SPLUNK_HOME'] + '/var/log/splunk/' + logFileName + '.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


logger = setup_logger()


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['url', 'username', 'password', 'proxy_url', 'proxy_port', 'proxy_username', 'proxy_password']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        logger.debug("Entring in function : handleList")
        logger.info("Gettiing stanza information from configuration file")

        stanza = "sn_instance"
        confDict = self.readConf("sn_sec_instance")
        config = {}
        if confDict is not None:
            config = confDict.get(stanza)
        else:
            logger.error("Could not read configuration")
            return
        if config is None:
            logger.error("Config for sn_instance not found")
            return

        clientId = config.get("clientId")
        clientSecret = config.get("clientSecret")
        authCode = config.get("auth_code")
        url = config.get("url") + "oauth_token.do"
        redirectUri = config.get("redirect_uri")
        proxyPassword = config.get("proxy_password")
        proxyUrl = config.get("proxy_url")
        proxyPort = config.get("proxy_port")
        proxyUsername = config.get("proxy_username")

        proxies = {}
        if proxyUrl:
            if "://" not in proxyUrl:
                proxyUrl = "https://{0}".format(proxyUrl)
            if proxyPort:
                proxyUrl = "{0}:{1}".format(proxyUrl, proxyPort)
            if proxyUsername and proxyPassword:
                proxyUrl = proxyUrl.replace("://", "://{0}:{1}@".format(proxyUsername, proxyPassword))
            proxies = {"http": proxyUrl, "https": proxyUrl}

        logger.info("Getting access token using authentication code")

        payload = 'grant_type=authorization_code&code=' + authCode + '&client_id=' + clientId + '&client_secret=' + \
                  clientSecret + '&redirect_uri=' + redirectUri
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        try:
            response = requests.request("POST", url, headers=headers, proxies=proxies, data=payload)
        except Exception as exception:
            logger.error("OAuth token request for primary splunk failed")
            logger.error(exception)
            response = {'status_code': 500, 'content': {'error_description': 'Internal Server Error'}}

        logger.debug("response : {}".format(response.text))
        logger.debug("Response status code : " + str(response.status_code))

        content = json.loads(response.content)

        # Check for any errors in response. If no error then add the content values in confInfo
        if response.status_code == 200:
            logger.info("Got access token Successfully")

            dt = datetime.now() + timedelta(seconds=content["expires_in"])
            dt = dt.replace(tzinfo=utc)
            expiryTime = datetime.strftime(dt, '%m-%d-%y %H:%M:%S')

            logger.debug("Token expiry time is : " + expiryTime)

            sessionkey = self.getSessionKey()
            cfm = conf_manager.ConfManager(sessionkey, "TA-ServiceNow-SecOps")
            cfm_inputs_conf = cfm.get_conf("sn_sec_instance")

            logger.debug("Updating conf file")

            cfm_inputs_conf.update(stanza, {"access_token": "*****", "refresh_token": "*****", "clientSecret": "*****",
                                            "proxy_password": "*****", "expiry_time": expiryTime})

            logger.debug("Conf file updated")
            logger.debug("encrypting keys")

            snutil.encryptToken(sessionkey, content["access_token"], content["refresh_token"], clientSecret,
                                proxyPassword)

            logger.debug("encryption is done successfully")
            logger.debug("Updated Configuration file with information successfully")

            for key, val in content.items():  # py2/3
                confInfo[stanza][key] = val
        else:
            # Else add the error message in the confinfo and logs
            logger.error("Did not receive access token")
            confInfo[stanza]["error"] = content["error_description"]

        logger.debug("Exit from function : handleList")


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
