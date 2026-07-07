import os, sys
import json, requests
import logging, re
import logging.handlers
from splunk.clilib import cli_common as cli
 
def getSelfConfStanza(stanza):
    appdir = os.path.dirname(os.path.dirname(__file__))
    apikeyconfpath = os.path.join(appdir, "default", "appdynamics_alert.conf")
    apikeyconf = cli.readConfFile(apikeyconfpath)
    localconfpath = os.path.join(appdir, "local", "appdynamics_alert.conf")

    if os.path.exists(localconfpath):
        localconf = cli.readConfFile(localconfpath)
        for name, content in localconf.items():
            if name in apikeyconf:
                apikeyconf[name].update(content)
            else:
                apikeyconf[name] = content
    return apikeyconf[stanza]

def setup_logger(level):
    logger = logging.getLogger('send_to_appdynamics')
    logger.propagate = False
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/appdynamics_alert_addon.log', maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.INFO)

def send_appdynamics_alert(payload):
    
    alert_log = ""
    try:
        payload = json.loads(payload)
        config = payload.get('configuration')

        result_link = payload.get('results_link')
        alert_title = payload.get('search_name')

        alert_log += "alert_name=\""+alert_title+"\""

        app_id = config.get('application_id')
        severity = config.get('severity')
        event_type = config.get('event_type')
        summary = config.get('summary')
        comment = config.get('comment')
        include_result_link = config.get('include_result_link')

        alert_log += " appdynamics_app_id="+app_id+" severity="+severity+" event_type=\""+event_type+"\" include_result_link="+include_result_link

        result_link = "<a href=\""+str(result_link)+"\">Splunk Results - "+str(alert_title)+"</a>"

        if int(include_result_link):
            comment = comment + "\n" + result_link

        stanza = getSelfConfStanza("appdynamics_alert")
        appdynamics_url = stanza['appdynamics_url']
        access_token = stanza['access_token']

        headers = {'Authorization': "Bearer " + access_token }

        event_params = {
            "severity":severity,
            "summary":summary,
            "eventtype":event_type,
            "comment":comment
        }

        api_url = re.sub("\/$","",appdynamics_url) + "/controller/rest/applications/"+str(app_id)+"/events"

        response = requests.request("POST", api_url, headers=headers, params=event_params)
        
        alert_log += " status=\""+response.text.strip()+"\""
        logger.info(alert_log)

    except Exception, e:
        logger.error(alert_log)
        logger.error("alert_name=\""+alert_title+"\" "+str(e))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        send_appdynamics_alert(sys.stdin.read())
    else:
        logger.error("Failed to execute alert action - Send to Appdynamics for" + str(sys.arg))
        sys.exit(1)