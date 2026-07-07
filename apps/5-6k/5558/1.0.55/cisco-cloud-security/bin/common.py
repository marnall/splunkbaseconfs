# encoding = utf-8
from __future__ import print_function

import json

class Common(object):
    def __init__(self):
        from os.path import dirname, abspath, sep, join
        self.bin_path = '{0}{1}'.format(dirname(abspath(__file__)), sep)
        self.splunk_path = ''
        for dir in (dirname(abspath(__file__))).split(sep):
            if dir == 'etc':
                break
            self.splunk_path = '{0}{1}{2}'.format(self.splunk_path, dir, sep)
        self.log_path = '{0}{1}'.format(join(self.splunk_path, 'var', 'log', 'splunk'), sep)
        self.ini_path = '{0}{1}'.format(join(self.splunk_path, "etc", "apps", "cisco-cloud-security", "ini"), sep)

    def _convert_to_dict(self, query):
        """
        Create a dictionary containing the parameters.
        """
        parameters = {}
        for key, val in query:
            # If the key is already in the list, but the existing entry isn't a list then make the
            # existing entry a list and add thi one
            # TODO :: change isinstance to type comparison
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
        params['form'] = self._convert_to_dict(params.get('form', []))
        params['query'] = self._convert_to_dict(params.get('query', []))
        return params
