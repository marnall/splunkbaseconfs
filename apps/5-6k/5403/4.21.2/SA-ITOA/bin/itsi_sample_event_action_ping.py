# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Ping is an example of an action that can be taken programmatically on one or
more Notable Events in ITSI.

It is implemented as a Splunk Modular Alert Action.

Chunk of the logic lies in the method `execute()` where we work on one event
at a time.

Using this as an example, you could implement other actions like telnet,
work on external ticket and then update your ITSI Event worklog, update status,
severity, owner etc...
"""

import sys
import json
import platform
import subprocess

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
import itsi_py3

from ITOA.setup_logging import getLogger
from ITOA.event_management.notable_event_utils import Audit

from itsi.event_management.sdk.grouping import EventGroup
from itsi.event_management.sdk.custom_group_action_base import CustomGroupActionBase


class Ping(CustomGroupActionBase):
    """
    Ping is an example of an action that can be taken, programmatically on an ITSI
    group. It is implemented as a Splunk Modular Alert Action.

    Usage::
        >>> if __name__ == "__main__":
        >>>     if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        >>>         input_params = sys.stdin.read()
        >>>         ping = Ping(input_params)
        >>>         ping.execute()
    """

    DEFAULT_HOST_KEY_IN_CONFIG = 'host_to_ping'
    DEFAULT_COUNT_VALUE = '10'  # packets
    DEFAULT_TIMEOUT_VALUE = '11'  # seconds

    def __init__(self, settings, count_value=None, timeout_value=None, audit_token_name='Auto Generated ITSI Notable Index Audit Token'):
        """
        Initialize the object
        @type settings: dict/basestring
        @param settings: incoming settings for this alert action that splunkd
            passes via stdin.

        @type count_value: basestring
        @param count_value: a string indicating the number of ICMP packets to
            send to destination.

        @type timeout_value: basestring
        @param timeout_value: (seconds) a string indicating the number of
            seconds to wait, prior to giving up in case of an ICMP timeout.

        @returns Nothing
        """
        self.logger = getLogger(logger_name="itsi.event_action.ping")

        super(Ping, self).__init__(settings, self.logger)

        self.executable = 'ping'
        self.count_flag = None
        self.count_value = None
        self.timeout_flag = None
        self.timeout_value = None
        self.platform_type = None
        self.audit = Audit(self.get_session_key(), audit_token_name)

        self._set_flags(count_value, timeout_value)

    def _set_flags(self, count_value, timeout_value):
        """
        Set some flags for count, timeout etc...
        We will consider the platform type for some of them.

        @type count_value: basestring
        @param count_value: a string indicating the number of ICMP packets to
            send to destination.

        @type timeout_value: basestring
        @param timeout_value: (seconds) a string indicating the number of
            seconds to wait, prior to giving up in case of an ICMP timeout.

        @returns Nothing
        """
        try:
            self.count_value = int(count_value)
        except (ValueError, TypeError):
            self.count_value = self.DEFAULT_COUNT_VALUE

        try:
            self.timeout_value = int(timeout_value)
        except (ValueError, TypeError):
            self.timeout_value = self.DEFAULT_TIMEOUT_VALUE

        # get platform specific flags
        if platform.system() == 'Windows':
            self.platform_type = 'windows'
            self.count_flag = '-n'
            self.timeout_flag = '-w'
        else:
            self.platform_type = '*nix'
            self.count_flag = '-c'
            self.timeout_flag = '-W'

        self.logger.debug('Environment/Platform=`%s`. Flags=`%s %s %s %s`',
                          self.platform_type, self.count_flag, self.count_value,
                          self.timeout_flag, self.timeout_value)

    def _get_exec_arg(self, host):
        """
        Return a list compatible with Popen which can be exec'ed

        @type host: basestring
        @param host: target host.

        @rtype: list of str
        @returns: a param consumed by Popen
        """

        self.logger.debug('Exec string=`%s %s %s %s %s %s`', self.executable,
                          self.count_flag, self.count_value, self.timeout_flag,
                          self.timeout_value, host)

        return [self.executable, self.count_flag, str(self.count_value), self.timeout_flag,
                str(self.timeout_value), host]

    def ping(self, host, group_id, policy_id):
        """
        given a host, ping it.

        @type host: basestring
        @param host: host to ping.

        @type group_id: basestring
        @param group_id: group id to ping

        @type policy_id: basestring
        @param policy_id: policy id of the group

        @rtype: tuple (basestring, basestring)
        @return: stdout, stderr
        """
        if any([not host, not isinstance(host, itsi_py3.string_type),
                isinstance(host, itsi_py3.string_type) and not host.strip()
                ]):
            message = 'Invalid host to ping. Received="%s". Type="%s"' % (host, type(host).__name__)
            self.audit.send_activity_to_audit({
                'event_id': group_id,
                'itsi_policy_id': policy_id
            }, message, 'Host Ping Failed')
            raise Exception(message)

        p = subprocess.Popen(
            self._get_exec_arg(host),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        out, err = p.communicate()

        self.logger.debug('Ping complete. host=`%s` stdout=`%s` stderr=`%s`', host, out, err)
        return itsi_py3.decode(out), itsi_py3.decode(err)

    def get_host_to_ping(self, data, host_key=None):
        """
        Return the string indicating the host to ping.
        Work on the config that came with the alert action execution
        if group specific config is provided.

        @rtype: basestring
        @return: the host to ping
        """
        host_key = self.DEFAULT_HOST_KEY_IN_CONFIG if not host_key else host_key
        config = self.get_config()
        host_info = config.get(host_key, '')

        host = None

        if host_info.startswith('%') and host_info.endswith('%'):
            # if host_info starts and ends with `%` it refers to
            # another key in the group data, whose value we care about.
            # We will retrieve its value and set it as the host.
            # {
            #    'host_to_ping': '%orig_host%', # references another field below
            #    ...
            #    'orig_host': 'foobar.orig',    # we care about this field
            #    ...
            # }
            host_info = host_info.strip('%')
            host = data.get(host_info)
        else:
            # if host_info does not start/end with `%s`, its value can be taken as
            # the value of the host to ping.
            host = host_info

        if host is None or (isinstance(host, itsi_py3.string_type) and not host.strip()):
            message = 'No host to ping.'
            self.logger.error(message)
            self.audit.send_activity_to_audit({'event_id': data.get('itsi_group_id')}, 'Failed to ping null host.', 'Host ping failed')
            raise Exception(message)

        # if host contains any port #s, strip it away
        # localhost:8000 or git.splunk.com:80
        host = host.split(':')[0]
        self.logger.debug('Host to ping=`%s`', host)
        return host

    def ping_and_update_notable_group(self, host, group_id, policy_id):
        """
        Do the act of pinging the host and then go on to update the comment for
        the notable event group.
        @type host: basestring
        @param host: host to ping

        @type group_id: basestring
        @param group_id: group id to ping

        @type policy_id: basestring
        @param policy_id: policy id of the group

        @rtype: basestring | None
        @return: error, if error occurred
        """
        out, err = self.ping(host, group_id, policy_id)
        error_to_return = None
        if err.strip():
            self.logger.error('Errors while running ping=`%s`', err)
            comment = 'Errors while running ping: {}'.format(err)
            error_to_return = comment
        else:
            self.logger.debug('Ping output=`%s`', out)
            comment = 'No errors while running ping.'

        self.logger.info('Updating tags/comments for group_id: %s', group_id)
        event = EventGroup(self.get_session_key(), self.logger)
        event.create_comment(group_id, comment, policy_id)
        if error_to_return is None:
            event.create_comment(group_id, out, policy_id)
            event.create_tag(group_id, 'ping', policy_id)
            self.audit.send_activity_to_audit({
                'event_id': group_id,
                'itsi_policy_id': policy_id,
            }, 'The host="%s" was pinged successfully.' % (host), 'Host pinged')
        else:
            self.audit.send_activity_to_audit({
                'event_id': group_id,
                'itsi_policy_id': policy_id
            }, 'Failed to ping host="%s".' % (host), 'Host ping failed')
        return error_to_return

    def execute(self):
        """
        Execute en bulk. For each event in the results file:
        1. extract the host to ping
        2. ping host
        3. add comment

        Apart from the above, this method does nothing else.
        The rest is left to your implementation and imagination.
        """
        self.logger.debug('Received settings from splunkd=`%s`', json.dumps(self.settings))

        count = 0
        try:
            ping_failed = False
            for data in self.get_group():
                if isinstance(data, Exception):
                    # Generator can yield an Exception
                    # We cannot print the call stack here reliably, because
                    # of how this code handles it, we may have generated an exception elsewhere
                    # Better to present this as an error
                    self.logger.error(data)
                    raise data

                if not data.get('itsi_group_id'):
                    self.logger.warning('Event does not have an `itsi_group_id`. No-op.')
                    continue

                group_id = data.get('itsi_group_id')
                policy_id = data.get('itsi_policy_id')
                host = self.get_host_to_ping(data)
                ping_error = self.ping_and_update_notable_group(host, group_id, policy_id)
                if ping_error is not None:
                    ping_failed = True
                count += 1
            if ping_failed is True:
                raise Exception('Failed to execute one or more ping actions.')
        except Exception as e:
            self.logger.error('Failed to execute ping.')
            self.logger.exception(e)
            sys.exit(1)

        self.logger.info('Executed action. Processed events count=`%s`.', count)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        input_params = sys.stdin.read()
        ping = Ping(input_params)
        ping.execute()
