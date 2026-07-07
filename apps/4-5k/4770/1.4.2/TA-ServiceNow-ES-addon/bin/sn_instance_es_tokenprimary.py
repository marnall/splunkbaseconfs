import os
import splunk.admin as admin
import logging, logging.handlers
import requests
import json
import pytz
from solnlib import conf_manager
from datetime import datetime, timedelta
import splunk.clilib.cli_common as cliLib

utc = pytz.UTC


def setup_logger():
    accessSettings = cliLib.getMergedConf("sn_sec_instance_es")
    level = accessSettings['splunk_log']['logLevel']
    logFileName = "TA_ServiceNow_ES_addon"
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
        logger.info("hit in setup")
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['url', 'username', 'password', 'proxy_url', 'proxy_port', 'proxy_username', 'proxy_password']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        logger.info("Getting stanza information from configuration file")
        stanza = "splunkes_primary"
        confDict = self.readConf("sn_sec_instance_es")
        primaryConfig = {}
        if confDict is not None:
            primaryConfig = confDict.get(stanza)
        if primaryConfig is None:
            logger.error("Primary config does not exist.")
            return
        clientId = primaryConfig.get("clientId")
        clientSecret = primaryConfig.get("clientSecret")
        authResp = primaryConfig.get("auth_code")
        url = primaryConfig.get("url") + "oauth_token.do"
        redirectUri = primaryConfig.get("redirect_uri")
        proxyPassword = primaryConfig.get("proxy_password")
        proxyUrl = primaryConfig.get("proxy_url")
        proxyPort = primaryConfig.get("proxy_port")
        proxyUsername = primaryConfig.get("proxy_username")
        logger.info("Getting access token using authentication code")
        payload = 'grant_type=authorization_code&code=' + authResp + '&client_id=' + clientId + '&client_secret=' + clientSecret + '&redirect_uri=' + redirectUri

        proxies = {}
        if proxyUrl:
            if "://" not in proxyUrl:
                proxyUrl = "https://{0}".format(proxyUrl)
            if proxyPort:
                proxyUrl = "{0}:{1}".format(proxyUrl, proxyPort)
            if proxyUsername and proxyPassword:
                proxyUrl = proxyUrl.replace("://", "://{0}:{1}@".format(proxyUsername, proxyPassword))
            proxies = {"http": proxyUrl, "https": proxyUrl}

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        logger.info("going to hit the end point")
        try:
            response = requests.request("POST", url, headers=headers, proxies=proxies, data=payload)
        except Exception as exception:
            logger.error("OAuth token request for primary splunk failed")
            logger.error(exception)
            response = {'status_code': 500, 'content': {'error_description': 'Internal Server Error'}}

        content = json.loads(response.content)

        # Check for any errors in response. If no error then add the content values in confInfo
        if response.status_code == 200:
            logger.info("Got access token Successfully")
            dt = datetime.now() + timedelta(seconds=content["expires_in"])
            dt = dt.replace(tzinfo=utc)
            expiryTime = datetime.strftime(dt, '%m-%d-%y %H:%M:%S')
            logger.debug("Token expiry time is : " + expiryTime)
            sessionkey = self.getSessionKey()
            cfm = conf_manager.ConfManager(sessionkey, "TA-ServiceNow-ES-addon")
            cfm_inputs_conf = cfm.get_conf("sn_sec_instance_es")
            cfm_inputs_conf.update(stanza,
                                   {"access_token": content["access_token"], "refresh_token": content["refresh_token"],
                                    "clientSecret": clientSecret, "proxy_password": proxyPassword,
                                    "expiry_time": expiryTime},
                                   ['access_token', 'refresh_token', 'clientSecret', 'proxy_password'])
            logger.debug("Updated Configuration file with information successfully")

            for key, val in content.items():  # py2/3
                confInfo[stanza][key] = val
        else:
            # Else add the error message in the confinfo and logs
            logger.error("Did not receive access token")
            confInfo[stanza]["error"] = content["error_description"]


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
