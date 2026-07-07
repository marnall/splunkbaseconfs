import requests as req
import sys, os
import json
import logging
import logging.handlers
import requests
import splunk.entity as entity
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from solnlib import credentials
#hack
import splunklib.client as client

appcontext = "onedrive_alert"

def setup_logger(level):
     logger = logging.getLogger('my_search_command')
     logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
     logger.setLevel(level)
     file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/'+appcontext+'.log', maxBytes=25000000, backupCount=5)
     formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
     file_handler.setFormatter(formatter)
     logger.addHandler(file_handler)
     return logger

def get_onedrive_session(clientid,tenantid,domain,password):
    data = {'grant_type':"client_credentials", 
        'resource':"https://graph.microsoft.com", 
        'client_id':clientid, 
        'client_secret':password} 
    URL = "https://login.windows.net/"+domain+"/oauth2/token?api-version=1.0"
    r = requests.post(url = URL, data = data) 
    j = json.loads(r.text)
    TOKEN = j["access_token"]
    headers={'Authorization': "Bearer " + TOKEN}
    return headers

logger = setup_logger(logging.INFO)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        logger.info(payload)
        config = payload.get('configuration')
        logger.info("config")
        logger.info(config)
        print( config, file=sys.stderr )
        event_result = payload.get('result')

        ent = entity.getEntity(['configs', 'conf-onedrive'],'Splunk OneDrive AlertAction', sessionKey=payload["session_key"], namespace="-", owner="-")
        if 'clientid' in ent and 'tenantid' in ent and 'domain' in ent:
            logger.info(ent)
            print( ent, file=sys.stderr )
            clientid = ent["clientid"]
            tenantid = ent["tenantid"]
            domain = ent["domain"]

        """
        Retrieve stored password, use https://splunkbase.splunk.com/app/4013 to create/update
        """
        cm = credentials.CredentialManager(payload["session_key"], "-", realm='onedrive_alert') #retrieve realm is vrops
        pwd = cm.get_password('Splunk OneDrive AlertAction')
        #print( pwd, file=sys.stderr )
        sid = payload["results_link"].split("=")[1] #hackish
        print( sid, file=sys.stderr )
        charttype = config["charttype"]
        print( charttype, file=sys.stderr )
        
        session = get_onedrive_session(clientid,tenantid,domain,pwd)
        
        #print( session, file=sys.stderr )
        #logger.info(session)

        """
        retrieve the xlsx for the sid
        """
        
        server_uri = payload["server_uri"] #'https://127.0.0.1:8089'            
        authToken = payload["session_key"]
        uri = "/services/Spreadsheet?job="+sid+charttype
        url = server_uri+uri
        print( url, file=sys.stderr )
        logger.info(url)

        """
        ugly, need to find out the CA stuff to do a secure rest call locally, maybe need to use splunklib to do it properly
        """
        try:
            # get os.path.expandvars(rootCAPath) read it from server.conf stanza sslConfig caCertFile = $SPLUNK_HOME/etc/auth/cacert.pem and use for verify

            logger.info("reading ssl settings from the conf via rest")
            print("reading ssl settings from the conf via rest", file=sys.stderr)
            resp = entity.getEntity(['configs'],'conf-server', sessionKey=authToken, namespace="-", owner="-")
            print("one", file=sys.stderr)
            print(resp, file=sys.stderr)
            resp = entity.getEntity(['configs', 'conf-server'],'sslConfig', sessionKey=authToken, namespace="-", owner="-")
            print("two", file=sys.stderr)
            print(resp, file=sys.stderr)
            sslconf = {}
            for k, v in resp.items():
                if str(v)=="None":
                    sslconf[str(k)] = ""
                else:
                    sslconf[str(k)] = str(v)
            logger.info( "ssl settings: ")
            logger.info( str(sslconf) )
            print( str(sslconf), file=sys.stderr)
            caCertFile = os.path.expandvars(sslconf["caCertFile"])
            logger.info(caCertFile)
            print( caCertFile, file=sys.stderr)

            if sslconf["sslVerifyServerName"] == 1:
                verify=caCertFile
            else:
                verify=False

            print( verify, file=sys.stderr)
            logger.info(verify)

            print( url, file=sys.stderr)
            logger.info(url)
           
            #"""
            r = requests.get(url, verify=verify, headers = { 'Authorization': ('Splunk %s' %authToken)})
            print( str(r.status_code), file=sys.stderr)
            logger.info( str(r.status_code) )
            filecontent = r.content
            print(filecontent, file=sys.stderr)



            """
            output to onedrive
            like so: PUT /drives/{drive-id}/items/{parent-id}:/{filename}:/content
            """
            r = requests.put(config["placement"] + ":/" + config["filename"] + ":/content", data=filecontent, headers=session)
            print( str(r.status_code), file=sys.stderr)
            logger.info( str(r.status_code) )
            print( r.text, file=sys.stderr)
            logger.info( r.text )

        except Exception as e:
            import traceback
            stack =  traceback.format_exc()
            print("exception: " + stack, file=sys.stderr)
            logger.error('invocation_id=%s invocation_type="%s" msg="some error occured - stack trace follows" %s' % (INVOCATION_ID,INVOCATION_TYPE, stack))
            exit()

    
if __name__ == "__main__":
    main()