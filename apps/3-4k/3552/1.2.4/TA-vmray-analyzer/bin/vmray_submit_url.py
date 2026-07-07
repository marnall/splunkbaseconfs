from __future__ import print_function
## Minimal set of standard modules to import
import csv
import gzip
import json
import logging
import sys

# pylint: disable=import-error
## Standard modules specific to this action
import time
from splunk.clilib import cli_common as cli

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(["etc", "apps", "TA-vmray-analyzer", "lib"]))
sys.path.append(make_splunkhome_path(["etc", "apps", "Splunk_SA_CIM", "lib"]))
from cim_actions import ModularAction, ModularActionTimer
from lib.rest_api import VMRayRESTAPI

logger = ModularAction.setup_logger('vmray_analyzer_submit_url_modalert')


## Subclass ModularAction for purposes of implementing
## a script specific dowork() method
class VMRayQueryModularAction(ModularAction):
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
        if self.configuration.get('url_value','') not in result:
            raise Exception('Parameter url_value does not exist in result')

        analyzer_general = cli.getConfStanza('vmray_analyzer_app_config', 'vmray_analyzer_general')
        ## Basic check
        api_key = analyzer_general.get('api_key')
        if not api_key and api_key.strip():
            raise Exception('API Key does not exist in conf or is empty')

    ## This method will do the actual work itself
    def dowork(self, result):
        analyzer_general = cli.getConfStanza('vmray_analyzer_app_config', 'vmray_analyzer_general')
        ## get parameter value
        if int(analyzer_general['disable_verify']) == 1:
            verify_ssl = False
        else:
            verify_ssl = True

        url = result[self.configuration.get('url_value')]
        apikey = analyzer_general['api_key']
        server_ip  = analyzer_general['server_ip']
        max_jobs = analyzer_general['max_jobs']

        # create VMRay REST API object
        api = VMRayRESTAPI(server_ip, apikey, verify_ssl)

        # add params
        params = {
            "sample_url": url,
            "tags": "Splunk,AdaptiveResponse",
            "max_jobs": max_jobs,
            "reanalyze": True
        }

        try:
            data = api.call("POST","/rest/sample/submit", params=params)
            sample = data["samples"][0]  # We excpect exactly one sample to be returned
            self.addevent(json.dumps(sample), sourcetype='vmray:ar:submiturl')
            self.message('Submit URL was sucessful', status='success')
        except Exception as exc:
            self.message('API request Failed',status='failure, '+ str(exc))
            raise Exception('API Request Failed')


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
        ## Retrieve an instance of VMRayQueryModularAction and name it modaction
        ## pass the payload (sys.stdin) and logging instance
        modaction = VMRayQueryModularAction(sys.stdin.read(), logger, 'VMRaySubmitURL')
        logger.debug(modaction.settings)
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
                    #modaction.message(result)
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
    except Exception as exc:
        ## adding additional logging since adhoc search invocations do not write to stderr
        try:
            modaction.message(exc, status='failure', level=logging.CRITICAL)
        except:
            logger.critical(exc)
        print("ERROR: %s" % exc, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv)
