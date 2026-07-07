# Phantom imports
import phantom.app as phantom
from phantom.app import BaseConnector
from phantom.app import ActionResult

import requests

from duo_auth import DuoAuth


class DuoConnector(BaseConnector):
    # Supported actions
    ACTION_ID_AUTHORIZE = 'authorize'
    ACTION_ID_TEST_ASSET_CONNECTIVITY = 'test_asset_connectivity'

    def __init__(self):
        super(DuoConnector, self).__init__()
        self.duo = requests.Session()
        self.api_host = None

    def initialize(self):
        config = self.get_config()
        self.api_host = config['api_host']
        self.duo.auth = DuoAuth(skey=config['skey'], ikey=config['ikey'])
        self.duo.verify = config[phantom.APP_JSON_VERIFY]
        return phantom.APP_SUCCESS

    def _authorize(self, param):
        user = param['user']
        request_type = param.get('type', 'Phantom request')
        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)
        self.save_progress('Getting authorization from ' + user)
        try:
            r = self.duo.post('https://' + self.api_host + '/auth/v2/preauth', data={'username': user})
            r.raise_for_status()
            r_json = r.json()['response']
            if r_json['result'] != 'auth':
                raise requests.HTTPError('user is not permitted to authenticate')
            r = self.duo.post('https://' + self.api_host + '/auth/v2/auth', data={'username': user,
                                                                                  'factor': 'push',
                                                                                  'device': 'auto',
                                                                                  'type': request_type,
                                                                                  'pushinfo': param.get('info')})
            r.raise_for_status()
            r_json = r.json()['response']
            action_result.add_data(r_json)
        except requests.HTTPError as e:
            action_result.set_status(phantom.APP_ERROR, 'Authentication request failed', e)
        else:
            if r_json['result'] == 'allow':
                action_result.set_status(phantom.APP_SUCCESS, 'Action authorized')
            else:
                action_result.set_status(phantom.APP_ERROR, 'Action not authorized')
            action_result.add_data(r_json)
        return action_result.get_status()

    def _test_asset_connectivity(self):
        try:
            r = self.duo.get('https://' + self.api_host + '/auth/v2/check')
            r.raise_for_status()
        except requests.HTTPError as e:
            return self.set_status_save_progress(phantom.APP_ERROR, 'Unable to connect to API server', e)
        return self.set_status_save_progress(phantom.APP_SUCCESS, 'Connections successful')

    def handle_action(self, param):
        ret_val = phantom.APP_ERROR
        action_id = self.get_action_identifier()
        if action_id == self.ACTION_ID_AUTHORIZE:
            ret_val = self._authorize(param)
        elif action_id == self.ACTION_ID_TEST_ASSET_CONNECTIVITY:
            ret_val = self._test_asset_connectivity()
        else:
            raise ValueError('Action {} is not supported'.format(action_id))
        return ret_val


if __name__ == '__main__':
    import simplejson as json
    import sys

    if len(sys.argv) < 2:
        print 'No test json specified as input'
        exit(0)
    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print json.dumps(in_json, indent=4)
        connector = DuoConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print json.dumps(json.loads(ret_val), indent=4)
    exit(0)
