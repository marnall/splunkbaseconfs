from schema import Schema, And, Use, Optional
import re

def environment_link_alternate_validator(url):
    # validate that the incoming environment_link_alternate is a link_alternate
    regex = re.compile(r'^([/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

# Shared scripted input source code reference
SCRIPTED_INPUT_SCRIPT = 'environment_poller.py'
INPUT_ROOT_NAME = '$SPLUNK_HOME/etc/apps/mothership/bin/%s' % SCRIPTED_INPUT_SCRIPT

search_schema = Schema({
    'name': And(str, len, error='Invalid name value'),
    'environment_link_alternate': And(str, len, environment_link_alternate_validator, error='Invalid environment_link_alternate value'),
    'search': And(str, len, error='Invalid search value'),
    'type': And(str, len, lambda val: val in ('inline', 'template'), error='Invalid type'),
    Optional('label'): And(str, len, error='Invalid label value'),
    Optional('disabled', default='False'): And(str, len, lambda val: val in ('True', 'False'), error='Invalid disabled value'),
    Optional('interval'): Use(int, error='Invalid interval value'),
    Optional('cron_schedule'): Use(str, error='Invalid cron schedule'),
    Optional('index_link_alternate'): And(str, len, error='Invalid index value'),
    Optional('lookup_link_alternate'): And(str, len, error='Invalid lookup value'),
    Optional('hec_endpoint'): And(str, len, error='Invalid HTTP Event Collector endpoint (hec_endpoint) value'),
    Optional('hec_token'): And(str, len, error='Invalid HTTP Event Collector token (hec_token) value'),
    Optional('sourcetype'): And(str, len, error='Invalid sourcetype value'),
})

SEARCH_FIELDS = ['name', 'label', 'environment_link_alternate', 'disabled', 'interval', 'cron_schedule','index_link_alternate', 'lookup_link_alternate', 'search', 'type', 'enable_metrics_search', 'poller_metrics_earliest_time', 'hec_endpoint', 'hec_token', 'sourcetype']

# Supported POST request arguments -- removes name for Splunk API expectations
ALL_FIELDS = list(set(SEARCH_FIELDS) - set(['name']))
OPTIONAL_FIELDS = list(set(SEARCH_FIELDS) - set(['name', 'type', 'search', 'environment_link_alternate']))
