import os, sys
import requests
from urllib.parse import parse_qs

APP_NAME = 'thinkst_canary_app'
splunkhome = os.environ['SPLUNK_HOME']
apphome = os.path.join(splunkhome, 'etc', 'apps', APP_NAME)
sys.path.append(os.path.join(apphome, 'vendor'))
#import rpdb
#sys.path.append('/usr/lib/python3.7/site-packages')

import splunk
from splunk.persistconn.application import PersistentServerConnectionApplication
import splunklib.client as client
import json

API_KEY_REALM='thinkst_canary_app_realm'
API_KEY_NAME='api_details'

class IncidentManager(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def _action_guts(self,requests_method, action, incident_id):
        url = f'https://{self.console_name}/api/v1/incident/{action}'
        payload = {
          'incident': incident_id
        }
        app_version = self.app_version
        splunk_version = self.splunk_version
        headers = {
            'User-Agent': f'Splunk API Call Thinkst App ({app_version}) Splunk ({splunk_version}) ',
            'X-Canary-Auth-Token': self.console_api_key
        }
        
        r = requests_method(url, data=payload, headers=headers)
        if r.status_code != 200:
            return {'payload': {'result': 'error', 'message': r.text}, 'status': 200}
        else:
            return {'payload': {'result': 'success', 'message': f'Incident {action}d'}, 'status': 200}


    def acknowledge(self, incident_id):
        return self._action_guts(requests.post, 'acknowledge', incident_id)

    def delete(self, incident_id):
        return self._action_guts(requests.delete, 'delete', incident_id)

    def handle(self, in_string):
        parameters = json.loads(in_string)

        if parameters['method'] != "POST":
            return {'payload': {'result': 'error', 'message': 'This endpoint takes POST requests only'}, 'status': 405}


        service = client.connect(
                app=APP_NAME,
                host=splunk.getDefault('host'),
                port=splunk.getDefault('port'),
                scheme=splunk.getDefault('protocol'),
                user=parameters['session']['user'],
                token=parameters['session']['authtoken'])

        canary_api_details = [ x for x in service.storage_passwords.list() if x['realm'] == API_KEY_REALM and x['username'] == API_KEY_NAME]
        if len(canary_api_details) == 0:
            return {'payload': {
                'result': 'error',
                'message': 'Please configure your Canary Console\'s API details in the Configuration tab'},
                'status': 200}
        elif len(canary_api_details) > 1:
            return {'payload': {
                'result': 'error',
                'message': 'Multiple API configurations were found in passwords.conf. Please remove them and reconfigure your App.'},
                'status': 200}

        try:
            canary_api_details=json.loads(canary_api_details[0].clear_password)
        except json.decoder.JSONDecodeError:
            return {'payload': {
                'result': 'error',
                'message': 'The API configuration found in passwords.conf is not valid. Please remove it and reconfigure your App.'},
                'status': 200}

        self.splunk_version = '.'.join([str(x) for x in service.splunk_version])
        app = [x for x in filter(lambda x: x.name == 'thinkst_canary_app', service.apps.list())][0]

        self.app_version = app['version']
        self.console_name = canary_api_details['console_name']
        self.console_api_key = canary_api_details['api_key']

        args = parse_qs(parameters['payload'])
        if args.get('action',[''])[0] == 'acknowledge':
            return self.acknowledge(args['incident'])
        elif args.get('action',[''])[0] == 'delete':
            return self.delete(args['incident'])
        else:
            return {'payload': {'result': 'error', 'message': 'Invalid action'}, 'status': 200}

    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")

    def done(self):
        pass
