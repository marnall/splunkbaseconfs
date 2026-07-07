
import sys
import json
import time
import uuid
import traceback
import requests
import socket
import splunk.Intersplunk
import splunk.entity as entity
import splunklib.client as client
import logging, logging.handlers
import splunk.clilib.cli_common as cliLib
import sn_connect as sncon

def generateCorrelationId():
    return uuid.uuid1(clock_seq=int(time.time())).hex
    
def generateEventSource():
    return "Splunk-{}".format(socket.gethostname())

def setCredentials(sessionKey, snPwd, prxPwd):
    service = client.connect(token=sessionKey, app="sn_sec_ops")
    try:
        service.storage_passwords.delete("instance", realm="snsec")
    except Exception, excpt:
        logging.info("Unable to delete storage_passwords: {}".format(excpt))
    try:
        service.storage_passwords.delete("proxy", realm="snsec")
    except Exception, excpt:
        logging.info("Unable to delete storage_passwords: {}".format(excpt))
            
    if snPwd not in [None, '']:
        service.storage_passwords.create(snPwd, "instance", realm="snsec")
    if prxPwd not in [None, '']:
        service.storage_passwords.create(prxPwd, "proxy", realm="snsec")
    
def getCredentials(sessionKey):
    snPwd = ""
    prxPwd = ""
    try:
        service = client.connect(token=sessionKey, app="sn_sec_ops")
        for password in service.storage_passwords:
            if password.name == "snsec:instance:":
                snPwd = password.clear_password
            if password.name == "snsec:proxy:":
                prxPwd = password.clear_password
    except Exception, excpt:
        logging.error("Unable to get storage_passwords: {}".format(excpt))
    
    if snPwd is None:
        snPwd = ""
    if prxPwd is None:
        prxPwd = ""
    return snPwd, prxPwd
  
def addEventValues(dataMap):
    if not dataMap.has_key('source'):
        dataMap["source"] = generateEventSource()
    if not dataMap.has_key('severity'):
        dataMap["severity"] = "3"
    if not dataMap.has_key('classification'):
        dataMap["classification"] = "1"

def addCorrelationValues(dataMap):
    if not dataMap.has_key('correlation_id'):
        dataMap['correlation_id'] = generateCorrelationId()
    if not dataMap.has_key('correlation_display'):
        dataMap['correlation_display'] = "Splunk"
    if not dataMap.has_key('external_url'):
        dataMap['external_url'] = "http://{0}:8000/app/search/search".format(socket.gethostname())
        
def handleResponse(statusCode, url, recordName):
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
    #Provide error message
    if not isSuccess:
        splunk.Intersplunk.parseError("ERROR Unable to create {0}, response code {1}{2} via REST call to {3}".format(recordName, statusCode, errorReason, url))
    return isSuccess
    
def createEventFromData(sessionKey, dataValues):
    accessSettings = cliLib.getMergedConf("sn_sec_instance")
    url = "{0}/api/now/table/{1}".format(accessSettings['sn_instance']['url'], "em_event")
    headers = {"Content-Type":"application/json","Accept":"application/json"}
 
    # Do the HTTP request
    response = sncon.postData(sessionKey, url, headers, dataValues)
    handleResponse(response.status_code, url, "event")
    
def createIncidentFromData(sessionKey, dataValues):
    accessSettings = cliLib.getMergedConf("sn_sec_instance")
    url = "{0}/api/now/table/{1}".format(accessSettings['sn_instance']['url'], "sn_si_incident_import")
    # Set proper headers
    headers = {"Content-Type":"application/json","Accept":"application/json"}
 
    # Do the HTTP request
    response = sncon.postData(sessionKey, url, headers, dataValues)
    handleResponse(response.status_code, url, "security incident")
