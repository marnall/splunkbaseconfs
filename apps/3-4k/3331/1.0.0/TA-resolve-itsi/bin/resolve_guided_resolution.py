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

LOGGER = setup_logging("resolve_guided_resolution.log", "ResolveGuidedResolution")

class ResolveGuidedResolution(CustomEventActionBase):
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
        super(Ping, self).__init__(settings, self.logger)

    def ping(self, host):
        '''given a host, ping it.
        @type host: basestring
        @param host: host to ping.

        @rtype: tuple (basestring, basestring)
        @return: stdout, stderr
        '''
        if any([
            not host,
            not isinstance(host, basestring),
            isinstance(host, basestring) and not host.strip()
            ]):
            raise Exception('Expecting host as valid string. Received: {}. Type: {}'.format(
                host, type(host).__name__))

        self.logger.info('Pinging host: {}'.format(host))
        p = subprocess.Popen(
                ["ping", "-c", "10", host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True)
        output, err = p.communicate()
        self.logger.debug('Complete. \nhost: {}\nstdout: {}\n stderr: {}'.format(
            host, output, err))
        return output, err

    def get_host_to_ping(self):
        '''return the a string indicating the host to ping
        @rtype: basestring
        @return: the host to ping
        '''
        config = self.get_config()
        if config is None:
            self.logger.error('No config received. Received: %s', self.settings)
            raise Exception('No input config received. Received: %s'%self.settings)
        host = config.get('host')
        if host is None:
            self.logger.error('No host to ping. Bailing out. Config: %s', config)
            raise Exception('No host to ping. Bailing out. Config: %s'% config)

        # if host contains any port #s, strip it away
        # locahost:8000 or git.splunk.com:80
        host = host.split(':')[0]
        return host

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
        host = self.get_host_to_ping()

        # We have a host to ping!
        try:
            out, err = self.ping(host)
        except Exception as exc:
            self.logger.error('Exception while pinging. Skipping.')
            self.logger.exception(exc)
            raise
        if err.strip():
            self.logger.error('Errors while running ping: {}'.format(err))
            comment = 'Errors while running ping: {}'.format(err)
        else:
            self.logger.info('No Errors while running ping.')
            self.logger.debug('Output: %s', out)
            comment = 'No Errors while running ping.'
        # ping complete, now lets add the comment. tag each event.

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
            self.logger.info('Updating tags/comments for event_id: {}'.format(
                event_id))
            event = Event(self.get_session_key(), self.logger)
            event.create_comment(event_id, comment)
            event.create_comment(event_id, out)
            event.create_tag(event_id, 'ping')
            count += 1

        self.logger.info('Number of events: {}'.format(count))
        return

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        input_params = sys.stdin.read()
        ping = Ping(input_params)
        ping.execute()
