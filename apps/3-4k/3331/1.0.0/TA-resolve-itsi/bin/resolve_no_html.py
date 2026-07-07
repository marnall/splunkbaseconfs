# Copyright (C) 2005-2016 Splunk Inc. All Rights Reserved.
"""
This is an example of what can be done programmatically as an action on an ITSI
Event. Chunk of the logic lies in the method execute()
We work on one event at a time.
After executing `ping`, you could potentially do one or more of the following:
    - add a tag / comment
    - update a tag / comment
    - delete a tag / comment
    - delete all tags / comments
The above (or more) is left to implementation.
"""

import sys
import json
import subprocess

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
from itsi.event_management.sdk.custom_event_action_base import CustomEventActionBase
from ITOA.setup_logging import setup_logging
from itsi.event_management.sdk.eventing import Event

LOGGER = setup_logging("resolve_no_html.log", "itsi.event_action.ping")

class ResolveNoHTML(CustomEventActionBase):
    '''This is an example of actions that can be taken, programmatically on an ITSI
    Event. Ping is one such action. You could potentially do a lot more, like
    telnet, create an external ticket and then update your ITSI Event worklog,
    update status, severity, owner etc...
    '''
    def __init__(self, settings):
        '''Initialize the object
        @type settings: dict/basestring
        @param settings: incoming settings that splunkd passes to use via stdin.
        '''
        self.logger = LOGGER
        self.logger.debug('Received settings: %s', settings)
        super(ResolveNoHTML, self).__init__(settings, self.logger)

    def execute(self):
        '''
        Runs ping on a host if available and leaves some room for more to
        happen. You could do stuff here like:
        - create an external ticket
        - update event worklog
        - update status, severity, owner etc...
        - update/add/remove tags
        - update/add/remove comments
        ...and so on. Apart from running ping, and updating comments, tags,
        this method does nothing else. That is left to your implementation.
        '''
        self.logger.info('Received settings from Splunkd: {}'.format(self.settings))

        count = 0

		for data in self.get_event():
            # generator can yield an Exception
            if isinstance(data, Exception):
                self.logger.exception(data)
                raise

            self.logger.debug('Received event data: %s', json.dumps(data))

            # Normalize Event Data. We will always work on a dictionary or try to atleast.
            if not isinstance(data, dict):
                try:
                    data = json.loads(data)
                except Exception as exc:
                    msg = ('We will only work with JSON type data. '
                        'Received: {}. Type: {}').format(data, type(data).__name__)
                    self.logger.error(msg)
                    self.logger.exception(exc)
                    continue
            if not data:
                self.logger.info('Nothing to do. Received no event data.')
                continue

            # Fetch the Event's `event_id`
            if not data.get('event_id'):
                self.logger.info('This event does not have an `event_id`. No-op.')
                continue # need to return sys.exit() here. but that is not needed for
                       # a PoC

            event_id = data.get('event_id')
			comment = "Resolve Systems touched the event."
            self.logger.info('Updating tags/comments for event_id: {}'.format(
                event_id))
            event = Event(self.get_session_key(), self.logger)
            event.create_comment(event_id, comment)
            event.create_comment(event_id, out)
            event.create_tag(event_id, 'ResolveNoHTML')
            count += 1

        self.logger.info('Number of events: {}'.format(count))
        return

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        input_params = sys.stdin.read()
        ping = Ping(input_params)
        ping.execute()
