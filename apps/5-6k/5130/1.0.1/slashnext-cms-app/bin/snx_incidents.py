import sys
sys.path.append('../lib')

import traceback
import time
import json
import splunk.Intersplunk
import snx_utils
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from SlashNextCMS import SlashNextIncidents


@Configuration()
class SnxIncidentsCommand(GeneratingCommand):
    # Class variables
    # Type of stat to fetch
    stat = Option(require=False)

    # The page number for API
    page = Option(require=False, validate=validators.Integer())

    # The rpp for API
    rpp = Option(require=False, validate=validators.Integer())

    # filters for Incident Listing API
    filters = Option(require=False)

    # sortby for Incident Listing API
    sortby = Option(require=False)

    # sortorder for Incident Listing API
    sortorder = Option(require=False)

    # searchkeyword for Incident Listing API
    searchkeyword = Option(require=False)

    # The thread ID
    incidentId = Option(require=False)

    # filtertype for Incident Filter Value API
    filtertype = Option(require=False)

    # Internal variables
    api_key = None
    base_url = None
    snx_logger = None

    def format_event(self, raw_json):
        event = dict()
        event['_time'] = time.time()
        event['_raw'] = json.dumps(raw_json)

        for (key, val) in raw_json.items():
            event[key] = val

        return event

    def generate(self):
        # Initial Settings for logging and credentials
        try:
            # Accquire the logger
            self.snx_logger = snx_utils.setup_logging()
            self.snx_logger.info('Running "snxincidents" Command')

            # Get API information
            api_config = snx_utils.get_config("slashnext.conf", "api-setup")
            self.base_url = api_config['base_url']
            self.api_key = api_config['api_key']

            self.snx_logger.info("Found API Key: {0} and Base URL: {1}".format(self.api_key, self.base_url))

            snx_incidents_api = SlashNextIncidents(self.api_key, self.base_url)

            self.snx_logger.info("Raw Filters: {0}".format(self.filters))
            if self.stat == 'incident_listing':
                if self.filters is not None:
                    # convert string representation of list to actual python list
                    self.filters = eval(self.filters)
                status, response = snx_incidents_api.\
                    list_incidents(self.filters, self.page, self.rpp, self.sortby, self.sortorder, self.searchkeyword)
                self.snx_logger.info("Getting Stat: {0} with filters: {1}, page: {2}, rpp: {3}, "
                                     "sortby: {4}, sortorder: {5} and searchkeyword: {6}"
                                     .format(self.stat, self.filters, self.page, self.rpp, self.sortby,
                                             self.sortorder, self.searchkeyword))
                yield self.format_event(response)
            elif self.stat == 'incident_detail':
                status, response = snx_incidents_api.incident_detail(self.incidentId)
                self.snx_logger.info("Getting Stat: {0} with incidentId: {1}".format(self.stat, self.incidentId))
                yield self.format_event(response)
            elif self.stat == 'incident_filter_value':
                if self.filters is not None:
                    # convert string representation of list to actual python list
                    self.filters = eval(self.filters)
                status, response = snx_incidents_api.incident_filters(self.filtertype, self.filters, self.searchkeyword)
                self.snx_logger.info("Getting Stat: {0} with filtertype: {1}, filters= {2} and searchkeyword: {3}"
                                     .format(self.stat, self.filtertype, self.filters, self.searchkeyword))
                yield self.format_event(response)
            else:
                yield {'ERROR': 'Please enter the correct value for stat'}
                return

        except Exception as e:
            stack = traceback.format_exc()
            splunk.Intersplunk.generateErrorResults(str(e))
            self.snx_logger.error(str(e) + ". Traceback: " + str(stack))


dispatch(SnxIncidentsCommand, sys.argv, sys.stdin, sys.stdout, __name__)