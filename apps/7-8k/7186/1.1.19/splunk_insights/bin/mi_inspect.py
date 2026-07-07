#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals
import os, sys
import time

if sys.version_info >= (3, 0):
    import configparser
else:
    import ConfigParser  as configparser
    
import socket

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from splunklib.six.moves import range


@Configuration(distributed=True)
class MiInspectCommand(GeneratingCommand):
    """
    The miinspect returns an event for each searched instance that has a measurable modular 
    input check point directory.  The checkpoint path size and file count is recorded. 

    Example:

    ``| miinspect splunk_server=sh-*``

    """
    splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
    splunk_server = Option( require=False, 
                            doc=''' **Syntax:** **splunk_server=***<value>*
                                    **Description:** Name of Splunk instances to search''')
    splunk_server_group = Option( require=False, 
                            doc=''' **Syntax:** **splunk_server_group=***<value>*
                                    **Description:** Name of Splunk search group to search''')
    summary = Option( require=False, default=True, validate=validators.Boolean() )
    checkpoint_path_size = 0
    checkpoint_file_count = 0
    


    def get_splunk_hostname(self):
        """ returns hostname for splunk_server field """
        serverconf_path = os.path.join(self.splunk_home, 'etc/system/local/server.conf')
        hostname = socket.gethostname()
        config = configparser.ConfigParser()
        try:
            config.read(serverconf_path)
            hostname = config.get('general', 'serverName')
        except Exception as e:
            self.logger.error('failed to return servername from path="{}", {}'.format(serverconf_path, e))
        return hostname


    def generate_event(self, hostname, path=None):
        evt_header = '{} Mod-Input CheckpointInspect'.format(time.strftime("%m-%d-%YT%T", time.localtime(time.time()))) 
        raw = '{} checkpoint_path_size_bytes="{}", checkpoint_file_count="{}" splunk_server="{}"'.format(evt_header, self.checkpoint_path_size, self.checkpoint_file_count, hostname)
        result = { '_time': time.time(), 
                    'checkpoint_path_size_bytes': self.checkpoint_path_size, 
                    'checkpoint_path_count': self.checkpoint_file_count,
                    'splunk_server': hostname,
                    '_raw': raw }
        if path:
            raw = '{}, path="{}"'.format(raw, path)
            result.update({'path': path, '_raw': raw })
        return result
        

    def generate(self):
        checkpoint_path = os.path.join(self.splunk_home, 'var/lib/splunk/modinputs')
        hostname = self.get_splunk_hostname()

        if os.path.isdir(checkpoint_path):
            for root, dirs, files in os.walk(checkpoint_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.checkpoint_path_size += os.path.getsize(file_path)
                    self.checkpoint_file_count += 1
                if not self.summary:
                    yield self.generate_event(hostname, path=root)
                    self.checkpoint_path_size = 0
                    self.checkpoint_file_count = 0

        if self.summary:
            yield self.generate_event(hostname)


dispatch(command_class=MiInspectCommand, argv=sys.argv, input_file=sys.stdin, output_file=sys.stdout, module_name=__name__)