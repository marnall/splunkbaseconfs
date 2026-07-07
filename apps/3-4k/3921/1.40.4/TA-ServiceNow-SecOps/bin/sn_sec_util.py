import json
import logging
import logging.handlers
import os
import socket
import time
import uuid
from datetime import datetime, timedelta

import pytz
import requests
import splunk.Intersplunk
import splunk.clilib.cli_common as cliLib

import sn_connect as sncon
import sn_sec_util as snutil
import splunklib.client as client
from dateutil import parser
from dateutil.tz import tzutc
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


def generateCorrelationId():
    return uuid.uuid1(clock_seq=int(time.time())).hex


def generateEventSource():
    return "Splunk-{}".format(socket.gethostname())


def setCredentials(sessionKey, snPwd, prxPwd):
    service = client.connect(token=sessionKey, app="TA-ServiceNow-SecOps")
    try:
        service.storage_passwords.delete("instance", realm="snsec")
    except Exception as excpt:
        logging.info("Unable to delete storage_passwords: {}".format(excpt))
    try:
        service.storage_passwords.delete("proxy", realm="snsec")
    except Exception as excpt:
        logging.info("Unable to delete storage_passwords: {}".format(excpt))

    if snPwd not in [None, '']:
        service.storage_passwords.create(snPwd, "instance", realm="snsec")
    if prxPwd not in [None, '']:
        service.storage_passwords.create(prxPwd, "proxy", realm="snsec")


def getCredentials(sessionKey):
    snPwd = ""
    prxPwd = ""
    try:
        service = client.connect(token=sessionKey, app="TA-ServiceNow-SecOps")
        for password in service.storage_passwords:
            if password.name == "snsec:instance:":
                snPwd = password.clear_password
            if password.name == "snsec:proxy:":
                prxPwd = password.clear_password
    except Exception as excpt:
        logging.error("Unable to get storage_passwords: {}".format(excpt))

    if snPwd is None:
        snPwd = ""
    if prxPwd is None:
        prxPwd = ""
    return snPwd, prxPwd


def addEventValues(dataMap):
    if 'source' not in dataMap:
        dataMap["source"] = generateEventSource()
    if 'severity' not in dataMap:
        dataMap["severity"] = "3"
    if 'classification' not in dataMap:
        dataMap["classification"] = "1"


def addCorrelationValues(dataMap):
    if 'correlation_id' not in dataMap:
        dataMap['correlation_id'] = generateCorrelationId()
    if 'correlation_display' not in dataMap:
        dataMap['correlation_display'] = "Splunk"
    if 'external_url' not in dataMap:
        dataMap['external_url'] = "https://{0}:8000/app/search/search".format(socket.gethostname())


def handleResponse(sessionKey, statusCode, url, recordName):
    isSuccess = False
    errorReason = ""
    if statusCode < 300 and statusCode >= 200:
        isSuccess = True
    if statusCode == 400:
        errorReason = ":Bad request"
    if statusCode == 401:
        errorReason = ":Unauthorized"
    if statusCode == 403:
        errorReason = ":Forbidden"
    if statusCode == 404:
        errorReason = ":Not found"
    if statusCode == 405:
        errorReason = ":Method not allowed"
    # Provide error message
    if not isSuccess:
        errorText = "ERROR Unable to create %s, response code %d %s via REST call to %s" % (
            recordName, statusCode, errorReason, url)
        snutil.createSplunkEvent(sessionKey, errorText)
        splunk.Intersplunk.parseError(errorText)
    return isSuccess


def parseTime(splunkTime):
    # We're converting into UTC and into a format ServiceNow is comfortable with
    # Splunk via UI gives an ISO string which we convert
    try:
        dt = parser.parse(splunkTime).astimezone(tzutc())
    except:
        # Splunk via alert gives epoch.
        try:
            dt = datetime.fromtimestamp(splunkTime)
        except:
            dt = datetime.utcnow()

    return dt.strftime("%Y-%m-%d %H:%M:%S")


def createEventFromData(sessionKey, dataValues):
    logger.debug("Invoking function: createEventFromData")
    accessSettings = cliLib.getMergedConf("sn_sec_instance")
    auth_type = accessSettings['sn_instance']['auth_type']
    if auth_type == "OAuth":
        logger.info("Creating Incident Using OAuth")
        createRecordFromDataUsingToken(accessSettings, dataValues, sessionKey, "em_event")
    else:
        url = "{0}/api/now/table/{1}".format(accessSettings['sn_instance']['url'], "em_event")
        # Set proper headers
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        response = sncon.postData(sessionKey, url, headers, dataValues)
        handleResponse(sessionKey, response.status_code, url, "event")
    logger.debug("Exiting function: createEventFromData")


def encryptToken(sessionKey, accesstoken, refreshtoken, clientsecret, proxyPassword):
    logger.debug('Invoking: encryptToken()')
    service = client.connect(token=sessionKey, app="TA-ServiceNow-SecOps")
    try:
        logger.debug("deleting previous access token encrypted key")
        service.storage_passwords.delete("accesstoken", realm="snsec")
        logger.debug("Deletion is done")
    except Exception as excpt:
        logging.info("Unable to delete storage_passwords: {}".format(excpt))
    try:
        logger.debug("deleting previous refresh token encrypted key")
        service.storage_passwords.delete("refreshtoken", realm="snsec")
        logger.debug("Deletion is done")
    except Exception as excpt:
        logging.info("Unable to delete storage_passwords: {}".format(excpt))
    try:
        logger.debug("deleting previous client secret encrypted key")
        service.storage_passwords.delete("clientsecret", realm="snsec")
        logger.debug("Deletion is done")
    except Exception as excpt:
        logging.info("Unable to delete storage_passwords: {}".format(excpt))
    try:
        logger.debug("deleting previous proxyPassword encrypted key")
        service.storage_passwords.delete("proxy_password", realm="snsec")
        logger.debug("Deletion is done")
    except Exception as excpt:
        logging.info("Unable to delete storage_passwords: {}".format(excpt))
    if accesstoken not in [None, '']:
        logger.debug("Creating encrypted key for access token")
        service.storage_passwords.create(accesstoken, "accesstoken", realm="snsec")
        logger.debug("Encryption is done")
    if refreshtoken not in [None, '']:
        logger.debug("Creating encrypted key for refresh token")
        service.storage_passwords.create(refreshtoken, "refreshtoken", realm="snsec")
        logger.debug("Encryption is done")
    if clientsecret not in [None, '']:
        logger.debug("Creating encrypted key for client secret")
        service.storage_passwords.create(clientsecret, "clientsecret", realm="snsec")
        logger.debug("Encryption is done")
    if proxyPassword not in [None, '']:
        logger.debug("Creating encrypted key for proxyPassword")
        service.storage_passwords.create(proxyPassword, "proxy_password", realm="snsec")
        logger.debug("Encryption is done")
    logger.debug('Exiting: encryptToken()')


def decryptToken(sessionKey):
    accesstoken = ""
    refreshtoken = ""
    clientsecret = ""
    proxyPassword = ""
    try:
        service = client.connect(token=sessionKey, app="TA-ServiceNow-SecOps")
        for password in service.storage_passwords:
            if password.name == "snsec:accesstoken:":
                accesstoken = password.clear_password
            if password.name == "snsec:refreshtoken:":
                refreshtoken = password.clear_password
            if password.name == "snsec:clientsecret:":
                clientsecret = password.clear_password
            if password.name == "snsec:proxy_password:":
                proxyPassword = password.clear_password
    except Exception as excpt:
        logging.error("Unable to get storage_passwords: {}".format(excpt))

    if accesstoken is None:
        accesstoken = ""
    if refreshtoken is None:
        refreshtoken = ""
    if clientsecret is None:
        clientsecret = ""
    if proxyPassword is None:
        proxyPassword = ""
    return accesstoken, refreshtoken, clientsecret, proxyPassword


def generateNewAccessToken(access_settings):
    logger.debug("generating new access token using refresh token")
    client_id = access_settings.get("clientId")
    client_secret = access_settings.get("clientSecret")
    url = access_settings.get("url") + "oauth_token.do"
    refresh_token = access_settings.get("refresh_token")
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


def storeNewAccessTokenInConfigFile(sessionKey, newAccessToken, refresh_token, expiry_time, clientSecret,
                                    proxy_password):
    logger.debug("Invoking function : storeNewAccessTokenInConfigFile")
    dt = datetime.now() + timedelta(seconds=expiry_time)
    dt = dt.replace(tzinfo=utc)
    tokenExpiryTime = datetime.strftime(dt, '%m-%d-%y %H:%M:%S')
    cfm = conf_manager.ConfManager(sessionKey, "TA-ServiceNow-SecOps")
    cfm_inputs_conf = cfm.get_conf("sn_sec_instance")
    input_stanza = "sn_instance"
    cfm_inputs_conf.update(input_stanza, {"access_token": "*****", "refresh_token": "*****", "clientSecret": "*****",
                                          "expiry_time": tokenExpiryTime})
    encryptToken(sessionKey, newAccessToken, refresh_token, clientSecret, proxy_password)
    logger.debug("Exit from function : storeNewAccessTokenInConfigFile")


def createRecordFromDataUsingToken(accessSettings, dataValues, sessionKey, eventIncidentEndpoint):
    responseMessage = ''
    api_type = accessSettings['sn_instance']['api_selection']
    if eventIncidentEndpoint == "sn_si_incident_import":
        responseMessage = "Security Incident"
    else:
        responseMessage = "Security Event"
        api_type = "table"
    logger.debug("Entring in function : createRecordFromDataUsingToken")

    expiryTime = datetime.strptime(accessSettings['sn_instance']["expiry_time"], '%m-%d-%y %H:%M:%S')
    expiryTime = expiryTime.replace(tzinfo=utc)
    currentTime = datetime.now()
    currentTime = currentTime.replace(tzinfo=utc)

    continueFlag = True
    access_token, refresh_token, client_secret, proxy_pwd = decryptToken(sessionKey)
    accessSettings['sn_instance']['clientSecret'] = client_secret
    accessSettings['sn_instance']['refresh_token'] = refresh_token
    accessSettings['sn_instance']['proxy_password'] = proxy_pwd
    logger.debug("checking expiry time of access token")
    if expiryTime < currentTime:
        logger.debug("access token expired !!")
        resp = generateNewAccessToken(accessSettings['sn_instance'])
        if resp["status_code"] == 200:
            access_token = resp["access_token"]
            logger.debug("storing and encrypting newly generated access token in configuration file")
            storeNewAccessTokenInConfigFile(sessionKey, resp["access_token"], resp["refresh_token"],
                                            resp["expiry_time"], accessSettings['sn_instance']['clientSecret'],
                                            proxy_pwd)
        else:
            continueFlag = False
            logger.error("failed : while generating access token using refresh token")
            logger.debug("Refresh token expired !!")
            handleResponse(sessionKey, resp.get('status_code'), resp.get('url'), responseMessage)
    else:
        logger.debug("access token not expired !!")

    if continueFlag == True:
        url = accessSettings['sn_instance'][
                  'url'] + "api/now/" + api_type + "/" + eventIncidentEndpoint  # accessSettings['sn_instance']['url'] + "api/now/table/sn_si_incident"
        payload = json.dumps({
            "short_description": "Oauth incident1"
        })
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + access_token
        }

        proxy_url = accessSettings['sn_instance']['proxy_url']

        if proxy_url:
            proxy_port = accessSettings['sn_instance']['proxy_port']
            proxy_user = accessSettings['sn_instance']['proxy_username']

            if not "://" in proxy_url:
                proxy_url = "https://{0}".format(proxy_url)
            proxyString = proxy_url

            if proxy_port:
                proxyString = "{0}:{1}".format(proxy_url, proxy_port)

            if proxy_user and proxy_pwd:
                proxyString = proxyString.replace("://", "://{0}:{1}@".format(proxy_user, proxy_pwd))
            proxies = {"http": proxyString, "https": proxyString}
            logger.debug("request url for incident from OAuth: " + url)
            logger.debug("request data for incident from Oauth: {0}".format(dataValues))
            response = requests.request("POST", url, proxies=proxies, headers=headers, data=dataValues)
            logger.debug("Response from Oauth: " + response.text)
            logger.debug("Response status code while creating record using OAuth: " + str(response.status_code))
        else:
            logger.debug("request url for incident from OAuth: " + url)
            logger.debug("request data for incident from Oauth: {0}".format(dataValues))
            response = requests.request("POST", url, headers=headers, data=dataValues)
            # content = json.loads(response.content)
            logger.debug("Response from Oauth: " + response.text)
            logger.debug("Response status code while creating record using OAuth: " + str(response.status_code))

        if response.status_code == 201:
            logger.info("Created record succesfully")
            logger.debug("Exit from function : createRecordFromDataUsingToken")
        else:
            logger.error("failed to create record")

        handleResponse(sessionKey, response.status_code, url, responseMessage)


def createIncidentFromData(sessionKey, dataValues):
    logger.debug("Entring in function : createIncidentFromData")
    accessSettings = cliLib.getMergedConf("sn_sec_instance")
    auth_type = accessSettings['sn_instance']['auth_type']
    api_type = accessSettings['sn_instance']['api_selection']
    if auth_type == "OAuth":
        logger.info("Creating Incident Using OAuth")
        createRecordFromDataUsingToken(accessSettings, dataValues, sessionKey, "sn_si_incident_import")
        logger.debug("Exit from function : createIncidentFromData")
    else:
        logger.info("Creating Incident Using Basic Auth")
        url = "{0}/api/now/{1}/{2}".format(accessSettings['sn_instance']['url'], api_type, "sn_si_incident_import")
        # Set proper headers
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        logger.debug("request url for incident from Basic Auth: " + url)
        logger.debug("request data for incident from Basic Auth: {0}".format(dataValues))
        response = sncon.postData(sessionKey, url, headers, dataValues)
        logger.debug("Response from Basic Auth: " + response.text)
        logger.debug("Response status code while creating record using Basic Auth: " + str(response.status_code))
        handleResponse(sessionKey, response.status_code, url, "security incident")
        logger.debug("Exit from function : createIncidentFromData")


def createSplunkEvent(sessionKey, text):
    service = client.connect(token=sessionKey, app="TA-ServiceNow-SecOps")
    indexName = "servicenow"
    try:
        index = service.indexes[indexName]
    except KeyError:
        service.indexes.create(indexName)
    event = "%s" % (text)
    service.post('/services/receivers/simple', index=indexName, sourcetype='servicenow', source='sn_sec_util.py',
                 body=event)
