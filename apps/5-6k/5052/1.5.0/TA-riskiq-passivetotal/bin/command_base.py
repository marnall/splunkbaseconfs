import ta_riskiq_passivetotal_declare
import sys
import datetime
import splunk.Intersplunk
import traceback
import six
import const

from passivetotal_utils import setup_logging, keep_keys, remove_keys, gen_label
from pt_client import PTClient

DATETIME_FORMAT = r"%Y-%m-%d %H:%M:%S"
CLASSIFICATION_LOOKUP = {
    'non-malicious': 1,
    'suspicious': 2,
    'malicious': 3,
    'unknown': 0,
    '': 0
}
PTPDNS_REMOVE_KEYS = ['value', 'recordHash', 'collected']
PTWHOIS_FIELDS = ['contactEmail', 'nameServers', 'registered', 'registryUpdatedAt', 'expiresAt', 'registrar']


class CommandPTClient(PTClient):
    """PassiveTotal Client specific for Custom Commands."""

    def _process_tab(self, tab, response, params):
        """Call process_<tab> and post_<tab>, if exists."""
        # General Processing
        func = 'process_{}'.format(tab)
        if hasattr(self, func):
            response = getattr(self, func)(response, params)

        # Post Processing
        func = 'customize_{}'.format(tab)
        if hasattr(self, func):
            response = getattr(self, func)(response, params)

        # Keep only required keys
        keys = '{}_KEYS'.format(tab.upper())
        if hasattr(const, keys):
            response = [keep_keys(result, getattr(const, keys)) for result in response]

        return response

    def customize_subdomains(self, response, params):
        """Customize subdomains."""
        query = response.get('primaryDomain', '')
        data = []
        for subdomain in response.get("subdomains", []):
            event = {'hostname': ('{}.{}'.format(subdomain, query)) if subdomain != query else subdomain}
            data.append(event)
        return data

    # Extra custom commands for back version support
    # Note: For below custom commands, keeping code same as in previous version to avoid any change conflict

    def process_ptcomponents(self, response, params):
        """Process ptcomponents."""
        return response.get('results', [])

    def process_ptphistory(self, response, params):
        """Process ptphistory."""
        data = []
        for item in response.get('teamstream', []):
            if item['type'] != 'search':
                continue
            data.append(item)
        return data

    def process_pthostpairs(self, response, params):
        """Process pthostpairs."""
        return response.get('results', [])

    def process_ptenrich(self, response, params):
        """Process ptenrich."""
        (enrichment, classification) = response
        tmp = classification.get('classification', 'unknown')
        if tmp == '' or not tmp:
            tmp = 'unknown'
        tmp = tmp.replace('_', '-')
        enrichment['tags'].append(tmp)
        try:
            enrichment['classification'] = CLASSIFICATION_LOOKUP[tmp]
        except Exception:
            enrichment['classification'] = -1

        return [enrichment]

    def process_ptpdns(self, response, params):
        """Process ptpdns."""
        data = []
        for result in response.get("results", []):
            result = remove_keys(result, PTPDNS_REMOVE_KEYS)
            result['count'] = response.get('totalRecords', 0)
            data.append(result)
        return data

    def process_ptssl(self, response, params):
        """Process ptssl."""
        data = []
        for result in response.get("results", []):
            ip_addresses = result.get('ipAddresses', [])
            result.pop('ipAddresses', None)
            for ip in ip_addresses:
                result['resolve'] = ip
                data.append(result)
            data.append(result)
        return data

    def process_pttrackers(self, response, params):
        """Process pttrackers."""
        return response.get('results', [])

    def process_ptupdns(self, response, params):
        """Process ptpudns."""
        data = []
        for result in response.get("frequency", []):
            tmp = {'resolve': result[0], 'count': result[1]}
            data.append(tmp)
        return data

    def process_ptwhois(self, response, params):
        """Process ptwhois."""
        data = []
        for field in PTWHOIS_FIELDS:
            tmp = {'key': gen_label(field), 'value': response.get(field, '')}
            data.append(tmp)
        for key, value in response.get('compact', {}).items():
            formatted = list()
            for item in value.get('values', []):
                tmp = "%s (%s)" % (item[0], ', '.join(item[1]))
                formatted.append(tmp)
            tmp = {'key': gen_label(key), 'value': ', '.join(formatted)}
            data.append(tmp)
        return data


class CommandBase(object):
    """Provide methods for working with custom command."""

    def __init__(self, tab, required_params=[], optional_params=[]):
        """Initialize object."""
        self.tab = tab
        self.required_params = required_params
        self.optional_params = optional_params

        self.options = dict()
        self.api_params = dict()
        self.session_key = None

        try:
            self.handle_stdin()
            self.pt_client = CommandPTClient(session_key=self.session_key)
        except Exception as ex:
            self.logger.error("Exception: {} -- Traceback: {}".format(ex, traceback.format_exc()))
            splunk.Intersplunk.generateErrorResults(str(ex))
            sys.exit(0)

    def handle_stdin(self):
        """Handle standard input at start."""
        input_events, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
        keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
        self.options = options
        self.session_key = settings.get("sessionKey")
        self.logger = setup_logging(session_key=self.session_key)

        # required params
        for param in self.required_params:
            value = options.get(param)
            # Strip leading '+' for phone numbers as API throws error
            if isinstance(value, six.string_types) and value.strip().lstrip("+"):
                self.api_params[param] = value.strip().lstrip("+")
            else:
                raise Exception('Please provide required parameter "{}".'.format(param))

        # optional params
        for param in self.optional_params:
            value = options.get(param)
            if isinstance(value, six.string_types) and value.strip():
                self.api_params[param] = value

        earliest = self.api_params.pop('earliest', None)
        if earliest and earliest.isdigit():
            try:
                start = datetime.datetime.fromtimestamp(int(earliest))
                self.api_params['start'] = start.strftime(DATETIME_FORMAT)
            except Exception:
                raise Exception('Invalid format of "earliest" parameter! Only epoch format is allowed.')

        latest = self.api_params.pop('latest', None)
        if latest and (latest.isdigit() or latest == 'now'):
            try:
                if latest == 'now':
                    end = datetime.datetime.now()
                else:
                    end = datetime.datetime.fromtimestamp(int(latest))
                self.api_params['end'] = end.strftime(DATETIME_FORMAT)
            except Exception:
                raise Exception('Invalid format of "latest" parameter! Only epoch format (or "now") is allowed.')

    def handle_stdout(self, output_events):
        """Handle stdout at the end."""
        splunk.Intersplunk.outputResults(output_events)
        self.logger.info('Received {} events'.format(len(output_events)))

    def start(self):
        """Start execution of custom command."""
        try:
            self.logger.info('Starting execution of custom command "{}"'.format(self.tab))
            self.logger.debug('Parameters received: {}'.format(self.options))
            self.logger.info("API params: {}".format(self.api_params))
            output_events = self.pt_client.get_tab(self.tab, self.api_params)
            self.handle_stdout(output_events)
            self.logger.info('Completed execution of custom command "{}"'.format(self.tab))
        except Exception as ex:
            self.logger.error("Exception: {} -- Traceback: {}".format(ex, traceback.format_exc()))
            splunk.Intersplunk.generateErrorResults(str(ex))
            sys.exit(0)
