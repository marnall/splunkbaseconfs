import sys
import json
import splunk
import splunklib.client
import splunklib.results
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from splunklib.searchcommands.validators import Boolean
import splunk.mining.dcutils
import time
from datetime import datetime, timedelta
import re
from asx_lib import ASXLib
from splunk.clilib import cli_common as cli


@Configuration(streaming=True, local=True)
class Executestory(GeneratingCommand):
    logger = splunk.mining.dcutils.getLogger()

    story = Option(doc='''
        **Syntax:** **story=***<story name>*
        **Description:** Story to update.
        ''', name='story', require=True, default=None)

    mode = Option(require=True)
    cron = Option(require=False)
    earliest_time = Option(require=False)
    latest_time = Option(require=False)

    def getURL(self):
        cfg = cli.getConfStanza('asx','settings')
        self.logger.info("executestory.py - asx_conf: {0}".format(cfg['api_url']))
        return cfg['api_url']

    def generate(self):

        if self.earliest_time:
            earliest_time = self.earliest_time
        if self.latest_time:
            latest_time = self.latest_time

        # connect to splunk and start execution
        port = splunk.getDefault('port')
        service = splunklib.client.connect(token=self._metadata.searchinfo.session_key, port=port, owner="nobody",app="Splunk_ASX")
        self.logger.info("executestory.py - starting ASX - {0} ".format(self.story))

        API_URL = self.getURL()
        asx_lib = ASXLib(service, API_URL)


        #Runnning the selected analytic story
        if self.mode == "now":

            #time attributes from time picker
            if hasattr(self.search_results_info, 'search_et') and hasattr(self.search_results_info, 'search_lt'):
                earliest_time = self.search_results_info.search_et
                latest_time = self.search_results_info.search_lt

            search_name = asx_lib.run_analytics_story(self.story, earliest_time, latest_time)

            yield {
                    '_time': time.time(),
                    'sourcetype': "_json",
                    '_raw': {
                            'analytic_story': self.story,
                            'search_name': search_name,
                            'mode': self.mode,
                            'status': "Successfully executed the searches in the analytic story"}

                             }

        #Schedule the selected analytic story if cron is selected
        if self.mode == "schedule":
            if self.cron:
                search_name = asx_lib.schedule_analytics_story(self.story, earliest_time, latest_time, self.cron)
                yield {
                        '_time': time.time(),
                        'sourcetype': "_json",
                        '_raw': {
                                    'analytic_story': self.story,
                                    'search_name': search_name,
                                    'mode': self.mode,
                                    'cron_schecule': self.cron,
                                    'status': "Successfully scheduled the analytic story"
                                }

                      }


        self.logger.info("executestory.py - completed ASX - {0} ".format(self.story))

    def __init__(self):
        super(Executestory, self).__init__()

dispatch(Executestory, sys.argv, sys.stdin, sys.stdout, __name__)
