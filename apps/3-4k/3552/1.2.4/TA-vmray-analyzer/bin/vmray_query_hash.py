from __future__ import print_function
## Minimal set of standard modules to import
import csv
import gzip
import json
import logging
import sys

## Standard modules specific to this action
import requests
import urllib
import time

from splunk.clilib import cli_common as cli

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "TA-vamray-analyzer", "lib"]))
sys.path.append(make_splunkhome_path(["etc", "apps", "Splunk_SA_CIM", "lib"]))
from cim_actions import ModularAction, ModularActionTimer
from lib.rest_api import VMRayRESTAPI

## Retrieve a logging instance from ModularAction
## It is required that this endswith _modalert
logger = ModularAction.setup_logger('vmray_analyzer_query_hash_modalert')


## Subclass ModularAction for purposes of implementing
## a script specific dowork() method
class VMRayQueryModularAction(ModularAction):
    VALID_HASHTYPES = ['md5','sha1','sha256'] 

    ## This method will initialize VMRayModularAction
    def __init__(self, settings, logger, action_name=None):
        ## Call ModularAction.__init__
        super(VMRayQueryModularAction, self).__init__(settings, logger, action_name)
        ## Initialize param.limit
        try:
            self.limit = int(self.configuration.get('limit', 1))
            if self.limit < 1 or self.limit > 30:
                self.limit = 30
        except:
            self.limit = 1

   ## This method will handle validation
    def validate(self, result):
        if self.configuration.get('hash_value', '') not in result:
            raise Exception('Parameter hash_value does not exist in result')

        if self.configuration.get('hash_type', '') not in VMRayQueryModularAction.VALID_HASHTYPES:
            raise Exception('Parameter hash_type does not exist is invalid')

        analyzer_general = cli.getConfStanza('vmray_analyzer_app_config', 'vmray_analyzer_general')    
        ## Basic check 
        v = analyzer_general.get('api_key')
        if not v and v.strip(): 
            raise Exception('API Key does not exist in conf or is empty')

        ## Hash value check
        v = result[self.configuration.get('hash_value')].strip()
        if v is None or not v.strip().isalnum(): 
            raise Exception('Parameter hash_value does not contain a valid hash value') 


    ## This method will do the actual work itself
    def dowork(self, result):
        analyzer_general = cli.getConfStanza('vmray_analyzer_app_config', 'vmray_analyzer_general')
        ## get parameter value
        if int(analyzer_general['disable_verify']) == 1:
            verify_ssl = False
        else:
            verify_ssl = True

        apikey = analyzer_general['api_key']
        server_ip = analyzer_general['server_ip']
        
        ## get parameter value
        value = result[self.configuration.get('hash_value')].strip()
        hash_type = self.configuration.get('hash_type')
        
        ## invoke VMRAy API
        api = VMRayRESTAPI(server_ip, apikey, verify_ssl)
        request_url = '/rest/sample/' + hash_type + '/' + value
        try:
            data = api.call('GET', request_url)
        except Exception as e:
            self.message('Failed to query for Hash', status='failure, ' + str(e))
            data = None
        
        if data:
            for sample in data:
                self.message('Successfully queried for Hash', status='success')
                self.addevent(json.dumps(sample), sourcetype='vmray:ar:queryhash')

def main(argv):
    ## This is standard chrome for validating that
    ## the script is being executed by splunkd accordingly
    if len(argv) < 2 or argv[1] != "--execute":
        print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
    analyzer_general = cli.getConfStanza('vmray_analyzer_app_config', 'vmray_analyzer_general')
    splunk_index = analyzer_general['index']
    vmray_server = analyzer_general['server_ip']

    ## The entire execution is wrapped in an outer try/except
    try:
        ## Retrieve an instanced of VMRayModularAction and name it modaction
        ## pass the payload (sys.stdin) and logging instance
        modaction = VMRayQueryModularAction(sys.stdin.read(), logger, 'VMRayQuery')
        logger.info(modaction.settings)
        logger.info(argv)
        splunk_index = analyzer_general['index']
        ## Add a duration message for the "main" component using modaction.start_timer as
        ## the start time
        with ModularActionTimer(modaction, 'main', modaction.start_timer):
            ## Process the result set by opening results_file with gzip
            with gzip.open(modaction.results_file, 'rb') as fh:
                ## Iterate the result set using a dictionary reader
                ## We also use enumerate which provides "num" which
                ## can be used as the result ID (rid)
                for num, result in enumerate(csv.DictReader(fh)):
                    ## results limiting
                    if num >= modaction.limit:
                        break
                    ## Set rid to row # (0->n) if unset
                    result.setdefault('rid', str(num))
                    ## Update the ModularAction instance
                    ## with the current result.  This sets
                    ## orig_sid/rid/orig_rid accordingly.
                    modaction.update(result)
                    ## Generate an invocation message for each result.
                    ## Tells splunkd that we are about to perform the action
                    ## on said r
                    modaction.invoke()
                    ## Validate the invocation
                    modaction.validate(result)
                    ## This is where we do the actual work.  In this case
                    ## we are calling out to an external API and creating
                    ## events based on the information returned
                    modaction.dowork(result)
                    ## rate limiting
                    time.sleep(1.6)

            ## Once we're done iterating the result set and making
            ## the appropriate API calls we will write out the events
            modaction.writeevents(index=splunk_index, host=vmray_server, source='vmrayanalyzer')

    ## This is standard chrome for outer exception handling
    except Exception as e:
        ## adding additional logging since adhoc search invocations do not write to stderr
        try:
            modaction.message(e, status='failure', level=logging.CRITICAL)
        except:
            logger.critical(e)
        print("ERROR: %s" % e, file=sys.stderr)

if __name__ == "__main__":
    main(sys.argv)
