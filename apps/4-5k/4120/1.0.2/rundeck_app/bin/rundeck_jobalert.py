'''
Custom Rundeck action alert to run a job

This module contains the logic to run the Rundeck job

June 2018

Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Rundeck, Inc. ( www.rundeck.com )
'''

import sys,os,hashlib,logging
import json
from splunklib.client import connect
from splunklib.client import Service
from splunklib.results import ResultsReader
import requests
from requests.utils import quote
from logging.handlers import TimedRotatingFileHandler

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

global myapp
myapp = 'rundeck_app'

#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var/log/splunk/rundeck_app_alertaction.log")

# Set up a specific logger
logger = logging.getLogger('Rundeck')

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)

def get_api_version(session_key,host):

    try:
        #default minimum
        api_version = "18"

        args = {'host':'localhost','port':SPLUNK_PORT,'token':session_key,'app':myapp,'owner':'nobody'}
        service = Service(**args)
        jobs = service.jobs

        # Run a blocking search
        kwargs_blockingsearch = {"exec_mode": "blocking"}
        searchquery_blocking = "`rundeck_host_info(%s)`" % host
        job = jobs.create(searchquery_blocking, **kwargs_blockingsearch)
        result_stream = job.results()
        reader = ResultsReader(result_stream)
        for item in reader:
            for key, value in item.items():
                if key == "api_version":
                    api_version = str(value)
        return api_version
    except: 
        e = sys.exc_info()[0]  
        logger.error("Error executing search to get api version : %s" % str(e))
        return api_version

def get_authtoken(session_key,host):

   try:
       logger.info("Getting Rundeck auth token from secure Splunk storage")
       args = {'host':'localhost','port':SPLUNK_PORT,'token':session_key,'app':myapp,'owner':'nobody'}
       service = Service(**args)
       storage_passwords = service.storage_passwords
       retrievedCredential = [k for k in storage_passwords if k.content.get('username')==host][0]
       if retrievedCredential is None:
           raise Exception("No auth token was found, have you setup the Rundeck App yet ?")
       else: 
           return retrievedCredential.clear_password

   except Exception, e:
      raise Exception("Could not get Rundeck auth token from Splunk. Error: %s"
                      % (myapp, str(e)))

def send_message(settings):

    try:
        log_level = logging.getLevelName(settings.get("log_level","INFO"))
        logger.setLevel(log_level)

        logger.debug("Running job with settings %s" % settings)

        job_id = settings.get('job_id')   

        host = settings.get("https_api_host")

        logger.debug(job_id)
        logger.debug(host)

        api_version=get_api_version(SESSION_TOKEN,host)
        endpoint='https://'+host+"/api/"+api_version+"/job/"+job_id+"/run"

        logger.debug("Job endpoint %s" % endpoint)

        url_args = {}

        job_as_user = settings.get('job_as_user')  
        job_run_at_time = settings.get('job_run_at_time')
        job_filter = settings.get('job_filter')
        job_argstring = settings.get('job_argstring')

        authtoken=get_authtoken(SESSION_TOKEN,host)  
        url_args['authtoken'] = authtoken

        if not job_as_user is None:
            url_args['asUser'] = job_as_user
        if not job_run_at_time is None:
            url_args['runAtTime'] = job_run_at_time
        if not job_filter is None:
            url_args['filter'] = job_filter
        if not job_argstring is None:
            url_args['argString'] = job_argstring

        logger.info("Running job")
        req_args = {"verify" : False ,"stream" : False , "timeout" : 60}

        if url_args:
            req_args["params"]= url_args

        try:                    
            logger.info("POSTing run job request to %s" % endpoint)
            logger.debug(req_args)
            r = requests.post(endpoint,**req_args)                   

        except Exception as e:
            logger.error("Exception performing request: %s" % str(e))
            return False

        try:
            r.raise_for_status()

        except requests.exceptions.HTTPError,e:
            error_output = r.text
            error_http_code = r.status_code
            logger.error("HTTP error: %s , HTTP error text: %s , HTTP error code: %s" % (str(e),error_output,error_http_code))
            return False

        logger.info("Job run complete")

        return True  
    except:  
        e = sys.exc_info()[0]  
        logger.error("Error trying to run Rundeck job: %s" % e)  
        return False  

if __name__ == "__main__":  
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":  
        payload = json.loads(sys.stdin.read())

        logger.debug(payload)
        server_uri = payload.get("server_uri")

        #setup some globals

        global SPLUNK_PORT
        global SESSION_TOKEN 

        SPLUNK_PORT = server_uri[18:]
        SESSION_TOKEN = payload.get("session_key")

        if not send_message(payload.get('configuration')):
            logger.error("Failed trying to run Rundeck job %s" % payload)
            sys.exit(2)
        else:
            logger.info("Rundeck job message successfuy POSTed")
    else:
        logger.critical("Unsupported execution mode (expected --execute flag)")
        sys.exit(1)
