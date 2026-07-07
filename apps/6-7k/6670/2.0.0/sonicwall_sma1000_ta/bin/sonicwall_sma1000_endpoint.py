#!/usr/bin/env python

import sys
import os
import json
import requests
import warnings
import urllib3.exceptions
from splunk.persistconn.application import PersistentServerConnectionApplication

if sys.platform == 'win32':
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


class Validate(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super().__init__()

    def flatten_query_params(self, params):
        flattened = {}
        for i, j in params:
            flattened[i] = flattened.get(i) or j
        return flattened

    def handle(self, in_string):
        try:
            params = self.flatten_query_params(json.loads(in_string)['query'])

            with warnings.catch_warnings():
                if params['validate_ssl'] == '0':
                    warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)

                response = requests.get(
                    url='https://{0}:{1}/Console/SystemStatus'.format(params['address'], params['port']),
                    auth=(params['username'], params['password']),
                    verify=params['validate_ssl'] == '1',
                    timeout=15.0
                )

            response.raise_for_status()
            data = response.json()

            # TODO: Validate the entire schema here
            if not data.get('applianceName'):
                raise Exception('Unrecognized response received from specified host.')

            return {'payload': {'success': True, 'host': data['applianceName']}, 'status': 200}
        except Exception as e:
            # TODO: User-friendly errors
            return {'payload': {'success': False, 'error': str(e)}, 'status': 500}
