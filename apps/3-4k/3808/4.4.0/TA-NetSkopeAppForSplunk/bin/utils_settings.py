"""Utilities related to settings page."""

import json
import six

from splunk import rest
from splunktaucclib.rest_handler.endpoint.validator import Validator
from netskope_utils import GetSessionKey, APP_NAME

BASE_STANZA_NAME = 'netskope_idx'
BASE_EVENT_TYPE_MAX_LEN = 8192


class SettingsValidator(Validator):
    """Class to validate input parameters."""

    def validate(self, value, data):
        """
        Validate settings.

        :return: True in case of validation success
        """
        base_event_type = data['base_event_type']
        session_key = GetSessionKey().session_key

        if isinstance(base_event_type, six.string_types) and len(base_event_type) > BASE_EVENT_TYPE_MAX_LEN:
            self.put_msg("Length of 'Base event type' should be between 0 to {}.".format(BASE_EVENT_TYPE_MAX_LEN))
            return False

        response = content = None
        try:
            # Store base event type into eventtypes.conf file
            args = {'search': base_event_type}
            response, content = rest.simpleRequest(
                "/servicesNS/nobody/{}/saved/eventtypes/{}?output_mode=json".format(
                    APP_NAME, BASE_STANZA_NAME),
                session_key,
                postargs=args,
                method='POST',
                raiseAllErrors=False
            )

            if response.status != 200:
                raise Exception()

        except Exception as ex:

            if response.status == 400:
                content = json.loads(content.decode())
                if 'messages' in content and content['messages'] and content['messages'][0].get('type', '') == 'ERROR':
                    self.put_msg(content['messages'][0]['text'])
                    return False

            self.put_msg('Error occured while storing Base event type: {}'.format(ex))
            return False

        return True


class EmailFieldValidator(Validator):
    """Class to validate input parameters ."""

    def validate(self, value, data):
        """
        Validate settings.

        :return: True in case of validation success
        """
        notification_status = int(data.get('email_enable', 0))
        enable_throttle = int(data.get('enable_throttle', 0))

        if notification_status:
            email_address = data.get('email_address', None)
            smtp_server = data.get('smtp_server', None)
            notify_after = data.get('notify_after', None)

            if email_address == "" or email_address is None:
                self.put_msg("Field 'Email Address(es)' is required.")
                return False

            if notify_after == "" or notify_after is None:
                self.put_msg("Field 'Notify If No Data Received For' is required.")
                return False

            if smtp_server == "" or smtp_server is None:
                self.put_msg("Field 'SMTP Server' is required.")
                return False

        if enable_throttle:
            throttle_duration = data.get('throttle_duration', None)
            if throttle_duration == "" or throttle_duration is None:
                self.put_msg("Field 'Suppress triggering for' is required.")
                return False

        return True
