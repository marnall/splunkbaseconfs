import sys
import os
import json
import traceback
import logging
import splunk
import requests
import time
import suds
from splunk.clilib import cli_common as cli
from datetime import datetime
from suds.xsd.doctor import Import
from suds.xsd.doctor import ImportDoctor
from suds.client import Client




# set up some logging
SCRIPT_PATH = os.path.join(os.environ["SPLUNK_HOME"], "var", "log", "splunk")
LOG_PATH = os.path.join(SCRIPT_PATH, "incman.log")

FORMATTER = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(filename=LOG_PATH, format=FORMATTER, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# This is where files added by the user via the splunk UI end up
STATIC_DATA = os.path.join(os.environ["SPLUNK_HOME"],
                           "etc", "apps", "Incman", "appserver", "static")

def main():
    """Script called by splunkd to create incident from template in Incman"""

    payload = json.loads(sys.stdin.read())
    configuration = payload.get('configuration', {})
    if not configuration:
        logger.error("Failed to get a incman configuration in the alert payload.")
        return


    session_key = payload.get('session_key', '')
    if len(session_key) == 0:
        logger.error("Did not receive a session key from splunkd.")
        return

    r = requests.get(
        url=splunk.getLocalServerInfo()+
        '/servicesNS/nobody/Incman/storage/passwords/%3Aincmanuser%3A?output_mode=json',
        headers={'Authorization': 'Splunk ' + session_key},
        verify=True)
    datajson = r.json()

    r2 = requests.get(url=splunk.getLocalServerInfo()+
                      '/servicesNS/nobody/Incman/storage/passwords/%3Aincmanapi%3A?output_mode=json',
                      headers={'Authorization': 'Splunk ' + session_key},
                      verify=True)

    datajson2 = r2.json()

    r3 = requests.get(url=splunk.getLocalServerInfo()+
                      '/servicesNS/nobody/Incman/incman/incmanendpoint/?output_mode=json',
                      headers={'Authorization': 'Splunk ' + session_key},
                      verify=True)

    datajson3 = r3.json()

    splunk_item = payload.get('result')
    configuration = payload['configuration']
    number_cef = datajson3['entry'][0]['content']['number_cef_field']
    cef = {}
    for numb in range(1, int(number_cef)+1):
        field = "cef_field_{number}".format(number=str(numb))
        value = "cef_value_{number}".format(number=str(numb))
        cef_field = configuration.get(field, "None")
        cef_value = configuration.get(value, "None")
        if cef_field != "None" and cef_value != "None" and cef_value != "":
            cef[cef_field] = cef_value

    json_cef = json.dumps(cef)
    incident_id = payload['configuration']['incidentID']
    append = configuration.get('create_new', "0")
    timelaps = configuration.get('timelaps', "0")
    incident_add_info = payload['configuration']['additionl_info']
    add_datetime = configuration.get('add_datetime', "None")
    incident_template = payload['configuration']['template']
    if int(append) == 0:
        append = "0"
    elif int(append) == 2:
        append = "1"
    else:
        append = "0"


    api_password = datajson2['entry'][0]['content']['clear_password']
    api_user = datajson3['entry'][0]['content']['apiuser']
    user = datajson3['entry'][0]['content']['user']
    host = datajson3['entry'][0]['content']['host']
    ssl = datajson3['entry'][0]['content']['ssl']
    user_password = datajson['entry'][0]['content']['clear_password']
    
    tns = "https://"+host+"/api/"
    client_url = "https://"+host+"/api/service.php?WSDL"

    imp = Import('http://schemas.xmlsoap.org/soap/encoding/')
    imp.filter.add(tns)
    client = Client(client_url, plugins=[ImportDoctor(imp)])
    token = client.service.auth_request_api(api_user, api_password)
    usertoken = client.service.auth_request_user(token, user, user_password)
    incident = client.factory.create('IMS_Incident')
    if add_datetime != 'None' and int(add_datetime) == 0 and int(append) == 0:
        incident.incidentid = "{incidentid} {datetime}".format(incidentid=str(incident_id), datetime=str(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))))
    else:
        incident.incidentid = incident_id

    incident.additional_info = incident_add_info
    incident.starttime = str(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time())))
    incident.reporttime = str(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time())))
    try:
        new_inc_id = client.service.incident_create_from_template(usertoken, incident, incident_template, json.dumps(splunk_item), str(json_cef), int(append), int(timelaps))
    except suds.WebFault, e:
        logger.error("Error during incident creation "+str(e))

    logger.debug("Payload "+str(configuration))
    logger.info("New incident created with id "+str(new_inc_id))


if __name__ == "__main__":
    try:
        logger.info("incman.py action script execution starting")
        main()
    except Exception, e:
        logger.error("Excecution Failed "+ str(e))
        logger.debug(traceback.format_exc())
        exit(1)
