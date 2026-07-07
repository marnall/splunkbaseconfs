# Copyright 2020 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from splunk.persistconn.application import PersistentServerConnectionApplication
import os, sys
import json
from glob import glob
import re
# from version import version
from time import sleep

# sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
# import splunk_debug as dbg
# dbg.enable_debugging(timeout=25)

# def version():
#     path = os.getenv('SPLUNK_HOME')
#     file = glob('{}/*-manifest'.format(path))[-1]
#     manifest = re.search(r"splunk-([^\-]+)-", file)[1]
#     return manifest

def version():
    path = os.path.join(os.getenv('SPLUNK_HOME'), 'etc', 'apps', 'splunkupgrader', 'bin')
    file = glob("{}/*.tgz".format(path))[-1]
    splunk_version = re.search(r"splunk-([^\-]+)-", file)[1]
    splunk_version = str(splunk_version)
    return splunk_version


class GetVersion(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

        
    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """
        args = self.parse_in_string(in_string)
        form_values = {}
        form_values = self.convert_to_dict(args.get('form', []))
        test_message = form_values['message']

        inst_version = version()
        
        payload = {}
        if inst_version == 'nofile':
            payload.update({'text': 'There isn\'t a Splunk install file present.'})
        else:
            payload.update({'text': 'Retreiving the install version.'})
            payload.update({'splunk_version': '{}'.format(inst_version)})
        return {'payload': payload, 'status': 200}

    def handleStream(self, handle, in_string):
        """
        For future use
        """
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass
    
    def convert_to_dict(self, query):
        """
        Create a dictionary containing the parameters.
        """
        parameters = {}

        for key, val in query:

            # If the key is already in the list, but the existing entry isn't a list then make the
            # existing entry a list and add thi one
            if key in parameters and not isinstance(parameters[key], list):
                parameters[key] = [parameters[key], val]

            # If the entry is already included as a list, then just add the entry
            elif key in parameters:
                parameters[key].append(val)

            # Otherwise, just add the entry
            else:
                parameters[key] = val

        return parameters

    def parse_in_string(self, in_string):
        """
        Parse the in_string
        """
        
        params = json.loads(in_string)
        

        params['method'] = params['method'].lower()

        params['form_parameters'] = self.convert_to_dict(params.get('form', []))
        params['query_parameters'] = self.convert_to_dict(params.get('query', []))

        return params

