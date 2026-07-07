#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Connectivity Test"""
import json
import logging
import os
import sys

from base_alert_action import BaseAlertAction
from base_launch_playbook import BaseLaunchPlaybook


class ArSendToPlaybook(BaseAlertAction, BaseLaunchPlaybook):
    """Adaptive Response Send to Playbook Action.

    Args:
        ta_name (str): The name of the App.
        alert_name (str): The name of the alert, used for log file name in
            "${SPLUNK_HOME}/var/log/splunk/" directory.
    """

    def __init__(self, ta_name, alert_name):
        """Initialize class properties."""
        super().__init__(ta_name, alert_name)

        # properties
        self.alert_name = alert_name
        self.filename = os.path.basename(__file__)

    @property
    def event_data(self):
        """Return events."""
        for event in self.get_events():
            for key in list(event):
                if key.startswith('__'):
                    del event[key]
                elif self.fields and key not in self.fields:
                    del event[key]
            yield event

    @property
    def fields(self):
        """Return fields input."""
        fields = self.get_param('fields') or ''  # uses self.configuration
        return [f.strip() for f in fields.strip().split(',') if f]

    def launch(self, event=None):
        """Launch playbook and return response."""
        self.message('Posting event', url=self.playbook_data.endpoint, event=event)
        r = self.launch_playbook('POST', body=event)
        if not r.ok:
            error = r.text or r.reason
            self.message(
                'Playbook exectution returned an error. Please ensure the playbook is enabled and '
                f'properly configured. ({error})',
                status='failure',
                level=logging.CRITICAL,
            )

        data = {
            'playbook': self.playbook_data.name,
            'playbook_endpoint': self.playbook_data.endpoint,
            'status': r.status_code,
            'length': len(r.content),  # using r.content as r.text is slow due to auto translation
        }

        try:
            # try and parse response as JSON
            data['response'] = r.json()
        except ValueError:
            # if JSON could not be parse insert response text into dict
            data['response'] = r.text
        except Exception:
            data['response'] = 'No Data Returned'

        return json.dumps(data)

    @property
    def playbook_key(self):
        """Return fields input."""
        return self.get_param('playbook_key').strip()

    def process_event(self, *args, **kwargs):  # pylint: disable=unused-argument
        """Process incoming event."""
        self.logger.debug(f'sys.argv: {sys.argv}')
        self.logger.debug(f'configuration: {self.configuration}')
        # this logs session_key and therefore should not be released
        # self.logger.debug(f'settings: {self.settings}')

        self.logger.info(f'Fields: {self.fields}')
        self.logger.info(f'Playbook Key: {self.playbook_key}')
        self.logger.info(f'Playbook Data: {self.playbook_data}')

        status = 0
        try:
            if not self.validate_params():
                return 3

            for event in self.event_data:
                data = self.launch(event)
                self.addevent(data, sourcetype='send_event_to_threatconnect_playbook:results')
                self.logger.debug(f'add event data: {data}')

            # write event
            # self.writeevents(index='summary', host='localhost', source='localhost')
            self.writeevents()
            self.message('Successfully executed a playbook', status='success')

        except (AttributeError, TypeError) as ae:
            self.log_error(
                f'Error: {ae}. Please double check spelling and also verify that a '
                'compatible version of Splunk_SA_CIM is installed.'
            )
            return 4
        except Exception as e:
            msg = 'Unexpected error: {}.'
            if e:
                self.log_error(msg.format(str(e)))
            else:
                import traceback

                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status

    def validate_params(self):
        """Validate input params."""
        if not self.playbook_key:
            self.log_error('Invalid value provided for required input playbook_key.')
            return False
        return True


if __name__ == '__main__':
    exitcode = ArSendToPlaybook('TA-threatconnect', 'tc_ar_send_to_playbook').run(sys.argv)
    sys.exit(exitcode)
