"""
    This file is used for xMatters Splunk ITSI Notable Event Alert Actions
"""
import sys
import six
import logging

# pylint: disable = import-error
# pylint: disable = wrong-import-position
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'xmatters_itsi', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from itsi_py3 import _
import itsi_py3

# import xmatters libraries
from common_utils.password import get_password
from xmatters_sdk.xm_event import XMattersEvent
from xmatters_sdk.xm_client import XMattersClient

# import ITSI libraries
from ITOA.setup_logging import setup_logging
from ITOA.event_management.notable_event_utils import Audit

from itsi.event_management.sdk.grouping import EventGroup
from itsi.event_management.sdk.custom_group_action_base import CustomGroupActionBase
# pylint: enable = wrong-import-position
# pylint: enable = import-error

# The name of the log file to write to
XM_ITSI_LOG = 'xmatters_itsi.log'

# The name of the password defining communication with xMatters
XMATTERS_PASSWORD_NAME = 'xmatters_itsi_password'

# The keys of the individual Grouped Events that will be added to the xm_event payload in
#   the event map property
EVENT_KEYS = [
    'alert_level',
    'alert_severity',
    'alert_value',
    'change_type',
    'composite_kpi_name',
    'description',
    'drilldown_uri',
    'event_description',
    'event_id',
    'health_score',
    'host',
    'linecount',
    'orig_index',
    'owner',
    'scoretype',
    'search_name',
    'service_ids',
    'severity',
    'severity_label',
    'source',
    'splunk_server',
    'tag',
    'time',
    'title',
]

# The keys of the parent event/group that will be added to the xm_event properties
CORRELATION_KEYS = [
    'alert_level',
    'alert_severity',
    'alert_value',
    'all_service_kpi_ids',
    'change_type',
    'composite_kpi_id',
    'composite_kpi_name',
    'description',
    'drilldown_search_earliest_offset',
    'drilldown_search_latest_offset',
    'drilldown_search_search',
    'drilldown_uri',
    'event_count',
    'event_description',
    'event_id', #is_required
    'event_identifier_fields',
    'event_identifier_hash',
    'event_identifier_string',
    'gs_search_source',
    'health_score',
    'host',
    'index',
    'is_active',
    'is_use_event_time',
    'itsi_first_event_id',
    'itsi_group_assignee',
    'itsi_group_count',
    'itsi_group_description',
    'itsi_group_id',
    'itsi_group_severity',
    'itsi_group_status',
    'itsi_group_title',
    'itsi_is_first_event',
    'itsi_is_last_event',
    'itsi_parent_group_id',
    'itsi_policy_id',
    'itsi_service_ids',
    'latest_alert_level',
    'linecount',
    'orig_index',
    'orig_sid',
    'orig_sourcetype',
    'owner',
    'scoretype',
    'search_name',
    'search_type',
    'service_ids',
    'severity_label',
    'severity_value',
    'severity',
    'source',
    'splunk_server_group',
    'splunk_server',
    'status',
    'tag',
    'time',
    'title',
]

# A mapping of severity values to their labels
SEVERITY_TO_LABEL = {
    '1': 'info',
    '2': 'normal',
    '3': 'low',
    '4': 'medium',
    '5': 'high',
    '6': 'critical'
}

# Defines which events to update
SHOULD_UPDATE_CORRELATION = True
SHOULD_UPDATE_CHILDREN = False

def build_xm_client(username, server_uri, session_key, logger):
    """
        Builds a new XMattersClient object
        @param username: <str> an optional xMatters Username
        @param server_uri: <str> the domain of the splunk server
        @param session_key: <str> a valid session key for the splunk server
        @return: <XMattersClient> an xMatters Client that can be used to make requests to xM API
    """
    xm_client = XMattersClient(logger=logger)
    if username:
        password = get_password(
            server_uri,
            session_key,
            XMATTERS_PASSWORD_NAME,
            logger=logger
        )
        if password is False:
            raise Exception('Error getting password: %s', XMATTERS_PASSWORD_NAME)
        xm_client.add_credentials(username, password)
    return xm_client

class XMattersITSI(CustomGroupActionBase):
    """
        The XMattersITSI class extends the CustomGroupActionBase and is used to
        send an Event to xMatters
    """

    def __init__(self, settings, count_value=None, timeout_value=None, audit_token_name='Auto Generated ITSI Notable Index Audit Token'):
        """
        Initialize the object
        @type settings: dict/basestring
        @param settings: incoming settings for this alert action that splunkd
            passes via stdin.

        @returns Nothing
        """
        self.logger = setup_logging(XM_ITSI_LOG, 'xmatters.itsi.event.action')

        super(XMattersITSI, self).__init__(settings, self.logger)

        config = self.get_config()
        username = config['username']

        self.xm_client = build_xm_client(
            username,
            self.settings.get('server_uri'),
            self.get_session_key(),
            self.logger
        )

        self.result = self.settings.get('result')
        self.endpoint_url = config['endpoint_url']
        self.recipients = config['recipients']
        self.priority = config['priority']

        self.audit = Audit(self.get_session_key(), audit_token_name)

        self.logger.info(
            'action=%s username=%s endpoint_url=%s recipients=%s priority=%s',
            'XM_ITSI_INIT',
            username,
            self.endpoint_url,
            self.recipients,
            self.priority
        )



    def get_prop_value(self, key, value):
        """
            Safely gets the value of a property for use in an xMatters Event.
            Currently supports list, str, unicode, None types

            @param key: <str> the name of the property
            @param value: <any> the value of the property
            @return: string
        """
        value_type = type(value)
        if value_type is list:
            return ','.join(value)
        # Use string_types to capture ascii and unicode encoded strings
        elif isinstance(value, six.string_types):
            return value
        elif value is None:
            return ''
        self.logger.warn('warning=INVALID_PROP_TYPE key=%s value_type=%s', key, value_type)
        return False


    def get_key_values_from_object(self, keys, source_object):
        """
            Helper method for getting a list of values from an object
            @param keys: <list>, a list of str representing the keys to extrat
            @param source_object: <dict>, a standard python map object
            @return: <dict> with only the selected keys
        """
        result = {}
        for key in keys:
            value = self.get_prop_value(key, source_object.get(key))
            if value is not False:
                result[key] = value
        return result


    def get_notable_event_xm_properties(self):
        """
            Helper method for getting the correlation event's properties
            @return: <dict> an object with only the keys we wish to send to xMatters
        """
        return self.get_key_values_from_object(CORRELATION_KEYS, self.result)


    def get_event_details(self, event):
        """
            Helper method for getting an event's properties that we are interested in
            @param event: <dict>, an event's details from the Notable Event SDK
            @return: <dict> an object with only the keys we wish to send to xMatters for the event
        """
        return self.get_key_values_from_object(EVENT_KEYS, event)


    def get_severity_label(self, event_details):
        """
            returns the label for the event's severity
            @param event_details: <dict>, an event's details from the Notable Event SDK
            @return: <str>, the label matching the event's severity
        """
        severity_value = event_details.get('severity')
        event_severity = SEVERITY_TO_LABEL.get(severity_value)
        if event_severity is None:
            self.logger.warning('type=BAD_SEVERITY severity=%s', severity_value)
            event_severity = 'other'
        return event_severity


    def add_success_comment_to_event(self, event_id, request_id):
        """
            Adds a success comment to an event
            @param event_id: <str> the event id
            @param request_id: <str> the request id received from xmatters
            @return: None
        """
        comment = 'Successfully sent request to xMatters: [%s]' % (request_id)
        event = EventGroup(self.get_session_key(), self.logger)
        event.create_comment(event_id, comment)

    def send_xm_event(self, groups_by_id, group_ids_by_severity):
        """
            Preps and sends an event to xMatters
            @param events_by_id: <dict> a dict of event ids to their event
            @param event_ids_by_severity: <dit> a dict of severities to a
                list of events with that severity

            @returns: <str|bool> If the request was successful, it will return
                the requestId from xMatters. Otherwise, False.
        """
        xm_event = XMattersEvent()
        properties = self.get_notable_event_xm_properties()
        for key in properties:
            xm_event.add_property(key, properties[key])

        xm_event.add_property('event_count', len(groups_by_id))
        xm_event.add_property('events_by_id', groups_by_id)
        xm_event.add_property('event_ids_by_severity', group_ids_by_severity)
        xm_event.add_property('xm_should_update_correlation', SHOULD_UPDATE_CORRELATION)
        xm_event.add_property('xm_should_update_children', SHOULD_UPDATE_CHILDREN)

        for recipient in self.recipients.split(';'):
            target_name = recipient.strip()
            xm_event.add_recipient(target_name)

        xm_event.set_priority(self.priority)

        return self.xm_client.send_event(self.endpoint_url, xm_event)

    def get_correlation_id(self):
        """
            Gets the Id of the Correlation Event
            @returns: <str|None> An event id if is available
        """
        return self.extract_group_or_event_id(self.result)

    def execute(self):
        """
            The execute method that actually handles the Notable Event Alert
            @return: None
        """
        correlation_id = self.get_correlation_id()
        if correlation_id is None:
            raise Exception('Missing correlation event_id')

        event_count = 0
        try:
            groups_by_id = {}
            group_ids_by_severity = {
                'critical': [],
                'high': [],
                'medium': [],
                'low': [],
                'normal': [],
                'info': [],
                'other': []
            }

            for data in self.get_group():
                if isinstance(data, Exception):
                    # Generator can yield an Exception
                    # We cannot print the call stack here reliably, because
                    # of how this code handles it, we may have generated an exception elsewhere
                    # Better to present this as an error
                    self.logger.error(data)
                    raise data

                group_id = data.get('itsi_group_id')
                if not group_id:
                    self.logger.warning('Event does not have a `group_id`. No-op.')
                    continue

                event_details = self.get_event_details(data)
                groups_by_id[group_id] = event_details
                event_count += 1

                group_ids_by_severity.get(self.get_severity_label(event_details)).append(group_id)

            request_id = self.send_xm_event(groups_by_id, group_ids_by_severity)
            if request_id is False:
                event = EventGroup(self.get_session_key(), logger=self.logger)
                msg = 'An error occurred while sending request to xMatters.'
                msg += ' See %s for details.' % XM_ITSI_LOG
                event.create_comment(
                    correlation_id,
                    msg
                )
                raise Exception('Failed to execute one or more send event actions.')
            self.logger.info('action=ALERT_EXECUTE success=true request_id=%s', request_id)

            if SHOULD_UPDATE_CORRELATION:
                self.add_success_comment_to_event(correlation_id, request_id)

            if SHOULD_UPDATE_CHILDREN:
                for event_data in groups_by_id.values():
                    group_id = event_data.get('itsi_group_id')
                    is_correlation_event = group_id != correlation_id
                    if is_correlation_event or self.should_update_correlation is not True:
                        self.add_success_comment_to_event(group_id, request_id)

# pylint: disable = broad-except
        except ValueError:
            pass # best case, try every event.
        except Exception as exception:
            self.logger.error('Failed to execute xM.')
            self.logger.exception(exception)
            sys.exit(1)
        return
# pylint: enable = broad-except

if __name__ == '__main__':
    LOGGER = setup_logging(XM_ITSI_LOG, 'xmatters.itsi', level=logging.INFO)
    if six.PY2:
        LOGGER.info('action=VERSION_CHECK version=python2')
    if six.PY3:
        LOGGER.info('action=VERSION_CHECK version=python3')
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        INPUT_PARAMS = sys.stdin.read()
        try:
            XM_ITSI = XMattersITSI(INPUT_PARAMS)
            XM_ITSI.execute()
# pylint: disable = broad-except
        except Exception as exception:
            LOGGER.error('Failed to execute xM.')
            LOGGER.exception(exception)
            raise exception
# pylint: enable = broad-except
