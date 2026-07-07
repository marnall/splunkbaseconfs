from splunk.persistconn.application import PersistentServerConnectionApplication
from constants import APP_NAME
from splunklib import client
import os
import sys
import json
import re
import logging
import splunk

cur_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.abspath(os.path.join(cur_dir, 'libs'))
sys.path.append(cur_dir)
sys.path.append(lib_path)


if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


sys.path.append(os.path.dirname(os.path.abspath(__file__)))
logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var',
                       'log', 'splunk', APP_NAME+'.log'])
logging.basicConfig(filename=logfile, level=logging.DEBUG)


class PanelHandler(PersistentServerConnectionApplication):
    PANEL_NAME_PATTERN = re.compile("^[a-zA-Z]([\w]*)$")

    def __init__(self, commandLine, commandArg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, inString):
        request = json.loads(inString)
        authToken = request['session']['authtoken']
        if request['method'] == 'GET':
            return self.getHandler(authToken, request['query'])
        elif request['method'] == 'POST':
            return self.postHandler(authToken, request['payload'])
        elif request['method'] == 'PUT':
            return self.putHandler(authToken, request['payload'])
        elif request['method'] == 'DELETE':
            return self.deleteHandler(authToken, request['query'])
        else:
            return {'payload': {}, 'status': 405}

    def create_collection(self, kvstore, data_type):
        last_ex = None
        collection_data = None
        try:
            kvstore.create(data_type)
            collections = kvstore.list()
            collection_data = None
            for c in collections:
                if c.data.collection.name == data_type:
                    collection_data = c.data
                    break
            assert collection_data, 'create collection ' + \
                str(data_type) + ' fails.'
        except Exception as e:
            last_ex = str(e)
        return collection_data, last_ex

    def parseGetParams(self, params):
        key = None
        for p in params:
            if p[0] == 'key':
                key = p[1]
        return (key)

    def _validate_panel_name(self, name):
        if name and self.PANEL_NAME_PATTERN.search(name):
            return True
        raise ValueError("Invalid panel name:" + name)

    def _validate_panel_frequency(self, freq):
        try:
            f = int(freq)
            assert f > 0
        except:
            raise ValueError("Invalid panel frequency:" + str(freq))

    # Add Custom Panel
    def postHandler(self, authToken, queryParams):
        try:
            kvstore = client.Service(
                token=authToken, app=APP_NAME, autologin=True
            ).kvstore
            collection_data = kvstore['userpanel'].data

        except Exception as e:
            logging.error(e)
            # create kvstore collection
            collection_data, error_msg = self.create_collection(
                kvstore, 'userpanel')

            if error_msg:
                payload = {'payload': {'error': error_msg}, 'status': 500}
                return json.dumps(payload)
        try:
            params = json.loads(queryParams)
            self._validate_panel_name(params.get('name'))
            self._validate_panel_frequency(params.get('frequency'))
            key = collection_data.insert(queryParams)
            payload = {'payload': {'content': key}, 'status': 200}
            return json.dumps(payload)

        except Exception as e:
            logging.error(e)
            payload = {'payload': {'error': str(e)}, 'status': 500}
            return json.dumps(payload)

    # Get custom panel
    def getHandler(self, authToken, query):
        try:
            kvstore = client.Service(
                token=authToken, app=APP_NAME, autologin=True).kvstore
            collection_data = kvstore['userpanel'].data.query()

            payload = {'payload': {
                'content': {
                    'entry': collection_data
                }}, 'status': 200}

            return json.dumps(payload)
        except Exception as e:
            logging.error(e)
            payload = {'payload': {
                'error': str(e)
            }, 'status': 500}
            return json.dumps(payload)

    # delete custom panel
    def deleteHandler(self, authToken, query):
        try:
            kvstore = client.Service(
                token=authToken, app=APP_NAME, autologin=True).kvstore
            collection_data = kvstore['userpanel'].data
            key = self.parseGetParams(query)
            queryString = json.dumps({
                '_key': key
            })
            collection_data.delete(query=queryString)

            payload = {'payload': {
                'content': {
                    'key': key
                }}, 'status': 200}
            return json.dumps(payload)
        except Exception as e:
            logging.error(e)
            payload = {'payload': {
                'error': str(e)
            }, 'status': 500}
            return json.dumps(payload)

    # put custom panel
    def putHandler(self, authToken, payload):
        try:
            kvstore = client.Service(
                token=authToken, app=APP_NAME, autologin=True).kvstore
            collection_data = kvstore['userpanel'].data
            params = json.loads(payload)
            self._validate_panel_name(params.get('name'))
            self._validate_panel_frequency(params.get('frequency'))
            key = params.get('key')
            collection_data.update(key, payload)
            payload = {'payload': {
                'content': {
                    'key': key
                }}, 'status': 200}
            return json.dumps(payload)
        except Exception as e:
            logging.error(e)
            payload = {'payload': {
                'error': str(e)
            }, 'status': 500}
            return json.dumps(payload)
