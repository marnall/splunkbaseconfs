"""Adaptive Response action to create a Threat Bulletin from Splunk ES Notables by populating a
template, looking for existing iocs in ThreatStream by value and adding the IOC ids"""

import csv
import time
import six
from datetime import datetime
import gzip
import json
import sys
import logging

from ts.settings import default_api_url, default_ui_url
from ts.optic_client import Optic
from util.splunk_access import SplunkAccess
from util.utils import normalise_log_level, verify_https_url

try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
    # noinspection PyUnresolvedReferences
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

sys.path.append(make_splunkhome_path(["etc", "apps", "Splunk_SA_CIM", "lib"]))

# noinspection PyUnresolvedReferences
from cim_actions import ModularAction

if six.PY3:
    file_open_mode = "rt"
else:
    file_open_mode = "r"
# set the maximum allowable CSV field size
#
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for
# the background on issues surrounding field sizes.
# (this method is new in python 2.5)
csv.field_size_limit(10485760)

cim_logger = ModularAction.setup_logger('analyzeioc_modalert')

body_template = '''
## {title}

### Splunk Incident
{notable_event}
'''
row_template = '''
__{label}__: {value}
'''

rule_labels = {
    "source": "Correlation Rule",
    "description": "Description",
    "urgency": "Urgency",
    "status_label": "Status",
    "owner": "Owner",
    "_time":"Created By",
    "orig_host": "Host",
    "orig_sourcetype": "Source Type",
    "src": "Source",
    "src_ip": "Source IP",
    "dest_ip": "Destination IP",
    "dest": "Destination",
    "url": "URL",
    "file_hash": "File Hash",
    "action": "Action"
    }
comment_template = '''
{review_time} {reviewer}

{comment}
'''
event_fields = ['_raw', 'sourcetype', 'source', 'host', '_time']


# ModularAction wrapper
class IOCAnalyzerModularAction(ModularAction):
    """Modular Alert action (Adaptive Response) to create a ThreatBulletin in ThreatStream from
    an ES Notable event"""

    def __init__(self, settings, logger, action_name=None):
        """
        This class will attempt to create an object in Optic from Splunk as a bulletin

        Args:
            settings: passed through from parent class
            logger: passed through from parent class
            action_name: passed through from parent class

        Required Splunk fields:
            src (str): Splunk CIM src expecting domain or IP
            dest (str): Splunk CIM dest expecting domain or IP

        Optional Splunk fields:
            index (str): defaults to 'notable'
            review_time
            reviewer
            drilldown_search
            drilldown_earliest
            drilldown_latest
            comment

        Mapped fields (event -> Optic)
            "source": "Correlation Rule",
            "description": "Description",
            "urgency": "Urgency",
            "status_label": "Status",
            "owner": "Owner",
            "_time":"Created By",
            "orig_host": "Host",
            "orig_sourcetype": "Source Type",
            "src": "Source",
            "src_ip": "Source IP",
            "dest_ip": "Destination IP",
            "dest": "Destination",
            "url": "URL",
            "file_hash": "File Hash",
            "action": "Action"
        """
        super(IOCAnalyzerModularAction, self).__init__(settings, logger, action_name)
        self.fields_to_analyze = self.configuration.get('field') or 'dest'
        self.fields_to_analyze = [f.strip() for f in self.fields_to_analyze.split(",")]
        self.tags = []
        tags = self.configuration.get("tags")
        if tags:
            self.tags = tags.split(',')
        # get optic credential
        splunkd = SplunkAccess(session_key=self.session_key, logger=logger)
        setup_config = splunkd.config.setup_config()
        logger.setLevel(normalise_log_level(splunkd.config.get_loglevel()))

        # Here we only support onprem connections or TS Cloud, not Integrator
        on_prem_url = setup_config.get("on_prem_url") if setup_config.get("on_prem_url") != \
            default_ui_url else None

        url = on_prem_url if on_prem_url else default_api_url
        url = verify_https_url(url)

        self.optic_client = Optic(url=url, logger=logger, splunka=splunkd)

    # Adds investigations based on result
    def analyze(self, event):
        iocs = [event.get(f) for f in self.fields_to_analyze]  # create a list of field values
        ioc_list = []
        for ioc in iocs:
            if ioc:
                ioc_list.extend(ioc.split('\n'))
        self.logger.info("field to analyze: %s", self.fields_to_analyze)
        self.logger.info("About to check for Suspect IOCs = %s, src:%s, dest:%s", iocs, event.get('src'), event.get('dest'))
        self.logger.debug("Event result %s", event)

        # step 1, check if self.ioc is an active intelligence in threatstream
        intel_ids = []
        try:
            intel_ids = self.optic_client.get_ioc_ids(ioc_list)
        except Exception as e:
            self.logger.exception(e)
        self.logger.info("Ids for %s is %s", iocs, intel_ids)
        index = event.get('index', "notable")
        if index == 'notable':
            # step 2, prepare a threat bulletin from an notable event
            bulletin = self._prepare_bulletin(event, intel_ids)
            self.logger.info("Creating a new bulletin: %s", json.dumps(bulletin))
            # step 3, create a threat bulletin
            self.optic_client.create_tip(bulletin)
            self.logger.info("Successfully created a new bulletin")

    def _prepare_bulletin(self, event, intel_ids):
        """Prepare the bulletin content from a notable event"""

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        bulletin = {}
        bulletin['intelligence'] = intel_ids
        bulletin['import_indicators_from_body'] = True
        bulletin['name'] = 'Splunk Adaptive Response: Threats discovered on %s' % now
        bulletin['tags'] = self.tags
        bulletin['body'] = body_template.format(
            title=self._replace_token(event['rule_title'], event).replace('\n', ' '),
            notable_event=self._build_rule(event),
           )
        bulletin['is_public'] = False
        self.logger.info("bulletin body: %s", bulletin['body'])
        return bulletin

    def _replace_token(self, value, event):  # type: (str, dict[str]) -> (str, None)
        """Replace tokens within the string `value` with the field values from the notable event
        Used mainly for when the ES notable title contains a reference to a field within the notable
        event. e.g. title='Attacker address detected at $src_ip$' we would resolve the  """
        if not value:
            return

        start = 0
        tokens = []
        while start < len(value):
            start = value.find('$', start)
            if start >= 0:
                end = value.find('$', start+1)
                if end >= 0:
                    tokens.append(value[start:end+1])
                    start = end+1
                else:
                    break
            else:
                break
        for token in tokens:
            replace_with = event.get(token[1:-1], "")
            value = value.replace(token, replace_with)
        return value

    def _build_rule(self, event):  # type: (dict[str]) -> str
        """This function populates the template variable *row_template* with the field values
        taken from the rule_labels list"""
        notable_event = ""
        # First, create the row for each required field in rule_labels variable
        for field, label in six.iteritems(rule_labels):
            if field == '_time':
                try:
                    time_value = int(event.get(field))
                except TypeError:
                    time_value = None
                value = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time_value))
            else:
                value = self._replace_token(event.get(field), event)
            if value:
                notable_event += row_template.format(label=label, value=value)

        # Secondly, add a row for each custom field that in specified in the configuration
        for field in self.fields_to_analyze:
            if field not in rule_labels:
                value = self._replace_token(event.get(field), event)
                notable_event += row_template.format(label=field, value=value)

        self.logger.debug("incident: %s", notable_event)
        return notable_event


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        six.print_("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)

    try:
        modaction = IOCAnalyzerModularAction(sys.stdin.read(), cim_logger, 'analyzeioc')
        if cim_logger.isEnabledFor(logging.DEBUG):
            cim_logger.debug('%s', json.dumps(modaction.settings, sort_keys=True,
                indent=4, separators=(',', ': ')))

        if six.PY2:
            cim_logger.info("Running under python2 environment")
        else:
            cim_logger.info("Running under python3 environment")

        # add status info
        modaction.addinfo()

        # get index
        index = modaction.configuration.get('index', 'notable')

        # get search name
        search_name = modaction.search_name or 'adhoc analyze ioc'

        # process results
        with gzip.open(modaction.results_file, file_open_mode) as fh:
            for num, result in enumerate(csv.DictReader(fh)):
                # set rid to row # (0->n) if unset
                result.setdefault('rid', str(num))
                modaction.update(result)
                modaction.invoke()
                result["rule_title"] = result.get("rule_title", search_name)
                modaction.analyze(result)
                modaction.addevent(modaction.result2stash(result, addinfo=True), 'stash')

        if modaction.writeevents(index=index, source=search_name):
            modaction.message('Successfully created splunk event', status='success', rids=modaction.rids)
        else:
            modaction.message('Failed to create splunk event', status='failure', rids=modaction.rids, level=logging.ERROR)

    except Exception as e:
        # adding additional logging since adhoc search invocations do not write to stderr
        try:
            cim_logger.exception(e)
            modaction.message(e, status='failure', level=logging.CRITICAL)
        except:
            cim_logger.critical(e)
        six.print_("ERROR Unexpected error: %s" % e, file=sys.stderr)
        sys.exit(3)
    else:
        cim_logger.info("Successfully executed Adaptive Response Action")
    finally:
        cim_logger.info("Finished executing Adaptive Response Action")
