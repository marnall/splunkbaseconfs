"""
    This file is used for xMatters Splunk Alert Actions
"""
import sys
import json
import six

# pylint: disable = import-error
# pylint: disable = wrong-import-position
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'xmatters_alert_action', 'lib']))

from common_utils.setup_logging import setup_logging
from common_utils.password import get_password
from xmatters_sdk.xm_event import XMattersEvent
from xmatters_sdk.xm_client import XMattersClient
# pylint: enable = wrong-import-position
# pylint: enable = import-error

# The name of the log file to write to
XM_ALERT_ACTION_LOG = 'xmatters_alert_action.log'

# The keys from the alert to send to the xMatters Event
KEYS = [
    'app',
    'cron.schedule',
    'description',
    'name',
    'next_scheduled_time',
    'owner',
    'results_link',
    'search',
    'trigger.date',
    'trigger.time',
    'type',
    'view_link',
    'alert.expires',
    'result.source',
    'result.host',
    'result.sourcetype',
    'result.splunk_server'
]

class XMattersAlert():
    """
        Class for the xMatters Alert Action handler
    """

    def __init__(self, settings):
        """
            @param settings: the payload from the alert action script call
        """
        self.logger = setup_logging(XM_ALERT_ACTION_LOG, 'xmatters.alert_actions')
        self.settings = settings
        self.config = settings.get('configuration')

        self.endpoint_url = self.config.get('endpoint_url')
        self.username = self.config.get('xMuser')
        self.recipients = self.config.get('recipients')
        self.session_key = settings.get('session_key')


    def get_prop_value(self, key, value):
        """
            Safely gets the value of a property for use in an xMatters Event. Currently supports
                list, str, unicode, None types
            @param key: <str> the name of the property
            @param value: <any> the value of the property
            @return: string
        """
        if value is None:
            return ''
        if isinstance(value, list):
            return ','.join(value)
        if isinstance(value, six.text_type):
            return value
        #else:
        self.logger.warn('warning=INVALID_PROP_TYPE key=%s value_type=%s', key, type(value))
        return False


    def execute(self):
        """
            Executes the Alert Action Handler
            @return: True, if successful
            @raises: Exception, if no request id is returned by xMatters
        """
        self.logger.info(
            "action=EXECUTE endpoint_url=%s username=%s recipients=%s",
            self.endpoint_url,
            self.username,
            self.recipients
        )
        xm_client = XMattersClient()
        if self.username:
            password_name = 'xmatters_password'
            password = get_password(
                self.settings['server_uri'],
                self.session_key,
                password_name
            )
            if password is False:
                raise Exception('Error getting password: %s' % password_name)
            xm_client.add_credentials(self.username, password)

        xm_event = XMattersEvent()
        for key in KEYS:
            value = self.get_prop_value(key, self.config.get(key))
            if value is not False:
                xm_event.add_property(key, value)

        for recipient in self.recipients.split(';'):
            target_name = recipient.strip()
            xm_event.add_recipient(target_name)

        xm_event.set_priority(self.config.get('priority'))

        request_id = xm_client.send_event(self.endpoint_url, xm_event)

        if request_id is False:
            self.logger.error(
                'An error occurred while sending request to xMatters. See %s for details.',
                XM_ALERT_ACTION_LOG
            )
            raise Exception('Failed to execute one or more send event actions.')
        return request_id



if __name__ == "__main__":
    try:
        LOGGER = setup_logging(XM_ALERT_ACTION_LOG, 'xmatters.alert_action.main')
        if six.PY2:
            LOGGER.debug('action=VERSION_CHECK version=python2')
        if six.PY3:
            LOGGER.debug('action=VERSION_CHECK version=python3')
        if len(sys.argv) > 1 and sys.argv[1] == "--execute":
            try:
                # Capture the input, which is a big JSON object
                # We stick it in a variable so we can print it if needed
                SYSTEM_IN = sys.stdin.read()
                INCOMING = json.loads(SYSTEM_IN)
                LOGGER.debug('Incoming %s', SYSTEM_IN)

                XM_ALERT = XMattersAlert(INCOMING)
                REQUEST_ID = XM_ALERT.execute()
                if REQUEST_ID:
                    LOGGER.info('action=ALERT_EXECUTE success=true request_id=%s', REQUEST_ID)
                else:
                    LOGGER.error('action=ALERT_EXECUTE success=false error=SEND_FAILURE')
                    sys.exit(2)

# pylint: disable = broad-except
            except Exception as exception:
                LOGGER.error('Failed to execute xMatters Alert Action')
                LOGGER.exception(exception)
                sys.exit(2)
        else:
            MESSAGE = 'Unsupported execution mode (expected --execute flag)'
            LOGGER.error('error=XM_MAIN_FAILURE message=%s', MESSAGE)
            sys.exit(1)
# pylint: disable = broad-except
    except Exception as exception:
        sys.stderr.write("FATAL xMatters encountered an exception")
        sys.stderr.write("FATAL xMatters encountered an %s" % json.dumps(exception))
        sys.exit(1)
# pylint: enable = broad-except
