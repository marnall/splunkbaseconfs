import sys
import requests
import os
import json
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import idefense_splunk
import splunklib.client

class checkapikey(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        PersistentServerConnectionApplication.__init__(self)

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """

        # Cleanup, set a config class that sets up logging
        file_name = os.path.splitext(os.path.basename(__file__))[0]
        validator = idefense_splunk.iDefense_splunk_base(file_name)
        in_dict = json.loads(in_string)

        session_key = in_dict['session']['authtoken']
        # The URI in the dict below is in the form, https://hostname:port,
        # using split will create list  [https, //hostname, port]
        # //hostname[2:] = hostname
        host = in_dict['server']['rest_uri'].split(':')[1][2:]
        port = in_dict['server']['rest_uri'].split(':')[2]

        validator.connect(splunklib.client.connect(token=session_key, host=host, port=port))
        payload = {
            'entry': [
                {
                    'name': 'Validation Result',
                    'content': ''
                }
            ]
        }

        try:
            check_connectivity = validator.idefense.queryUrl(params=[])

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                payload['entry'][0]['content'] = "Invalid Authentication. Bad or Expired API Key"
                return {'payload': payload, 'status': 200}

            else:
                validator.logger.info("The API Server returned error code {}".format(e.response.status_code))
                payload['entry'][0]['content'] = "The API Server returned error code {}".format(e.response.status_code)
                return {'payload': payload, 'status': e.response.stats_code}

        except requests.exceptions.ConnectionError as e:
            payload['entry'][0]['content'] = "Connection Timed Out. Please check connectivity to the Server"
            return {'payload': payload, 'status': 200}

        if "results" in check_connectivity.keys():
            payload['entry'][0]['content'] = "Sucessfully Connected to the API Endpoint"
            return {'payload': payload, 'status': 200}

        else:
            payload['entry'][0]['content'] = "Unexpected Response from the API server"
            return {'payload': payload, 'status': 200}

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass
