# encoding = utf-8

''' Script for modular alert action that allows you to ad hoc query for ACTI Threat Indicators.'''

import csv      ## Result set is in CSV format
import gzip     ## Result set is gzipped
import logging  ## For specifying log levels
import sys
import traceback
import json
## Importing the cim_actions.py library
## A.  Import make_splunkhome_path
## B.  Append your library path to sys.path
## C.  Import ModularAction from cim_actions
## D.  Import ModularActionTimer from cim_actions
from splunk.clilib.bundle_paths import make_splunkhome_path
# import our cim_actions.py library
# from Splunk_SA_CIM
sys.path.append(make_splunkhome_path(["etc", "apps", "Splunk_SA_CIM", "lib"]))
from cim_actions import ModularAction

#Splunk Library for Splunk
import idefense_splunk
import splunklib.client

ACTION_NAME = "query_acti"
LOGGER_NAME = ACTION_NAME + "_modalert"

## Retrieve a logging instance from ModularAction
## It is required that this endswith _modalert
logger = ModularAction.setup_logger(LOGGER_NAME)



class ACTIQueryModularAction(ModularAction):

    def __init__(self, settings, logger, action_name=None):
        ## Call ModularAction.__init__
        super(ACTIQueryModularAction, self).__init__(settings, logger, action_name)

    

    def run(self, argv):
        status = 0
        if len(argv) < 2 or argv[1] != "--execute":
            msg = 'Error: argv="{}", expected="--execute"'.format(argv)
            print(msg, file=sys.stderr)
            sys.exit(1)
        self.prepare_meta_for_cam()

    #The method below sets rid and sid for Splunk ES
    def prepare_meta_for_cam(self):
        try:
            try:
                rf = gzip.open(self.results_file, 'rt')
            except ValueError:  # Workaround for Python 2.7 on Windows
                rf = gzip.open(self.results_file, 'r')
            for num, result in enumerate(csv.DictReader(rf)):
                result.setdefault('rid', str(num))
                self.update(result)
                self.invoke()
                break
        finally:
            if rf:
                rf.close()


    ## This method will do the actual querying
    def query_acti(self):

        indicator_value = self.configuration.get('indicator') 
        #Need a splunk session to setup Splunk ACTI object
        query_params = {'key__values': indicator_value}

        splunk_session_key = self.settings.get('session_key')
        splunk_host = self.settings.get('server_host')
        splunk_port = self.settings.get('server_uri').split(':')[-1]

        acti_instance = idefense_splunk.iDefense_splunk_base(LOGGER_NAME)
        acti_instance.connect(splunklib.client.connect(token=splunk_session_key, host=splunk_host, port=splunk_port))
        
        result = acti_instance.idefense.queryTI(params=query_params)
        sourcetype = ACTION_NAME
        
        if 'results' not in result:
            self.addevent(f"Got response with no requests from server for query {indicator_value}", sourcetype=sourcetype)

        elif len(result['results']) > 0:
            self.addevent(f"Got response from server for query {indicator_value}", sourcetype=sourcetype)
            result = {'query': indicator_value, 'has_result':'yes', 'result': result['results'][0]}
        else:
            result = {'query': indicator_value, 'has_result':'no'}

        self.addevent(json.dumps(result), sourcetype=sourcetype)
        self.message(f"Ran {ACTION_NAME} response action", status='success', level=logging.INFO)

if __name__ == "__main__":
    try:
        modaction = ACTIQueryModularAction(sys.stdin.read(), logger, ACTION_NAME)
        #logger.info(modaction.settings)
        modaction.run(sys.argv)
        modaction.query_acti()
        modaction.writeevents(index='_internal', source=ACTION_NAME )
    
    except Exception as e:
        try:
            modaction.message(e, status='failure', level=logging.CRITICAL)
            modaction.message(traceback.format_exc(), status='failure', level=logging.CRITICAL)
        except:
            logger.critical("critical error, exiting")
            logger.critical(e)
        print(sys.stderr)
        sys.exit(3)