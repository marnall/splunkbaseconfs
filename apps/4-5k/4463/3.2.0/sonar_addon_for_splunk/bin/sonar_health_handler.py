import json
import os
import sys

import splunk.persistconn.application as app

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.six.moves.urllib.request import Request, urlopen
from splunklib.six.moves.urllib.error import URLError

class SonarHealthHandler(app.PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(app.PersistentServerConnectionApplication, self).__init__()

    def handle(self, in_string):
        """
        Request the Sonar health endpoint to determine a configuration's connection status
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """
        in_string_dict = json.loads(in_string)
        data_obj = in_string_dict.get("form")

        if not data_obj:
            return self.format_error("No data provided, data fields 'address' and 'port' are required", 400)

        data = self.parse_data_obj(data_obj)
        if isinstance(data, str):
            return self.format_error(data, 400)

        elif ("address" not in data) or ("port" not in data):
            return self.format_error("Data fields 'address' and 'port' are required", 400)

        req = Request(f"https://{data.get('address')}:{data.get('port')}/health")

        try:
            res = urlopen(url=req, timeout=30)
            health_response = res.read().decode("utf-8")
            health_status_code = str(res.status)

            if health_status_code != "200" or health_response != "UP":
                return self.format_error(f"Unexpected response received: {health_response}, Status: {health_status_code}", health_status_code)

        except URLError:
            return self.format_error(f"Connection timed out after 30 seconds.", 408)

        output = {
            "health_response": health_response,
            "health_status_code": health_status_code
        }

        return {"payload": output, "status": 200}

    def parse_data_obj(self, data):
        """
        Parsing provided data from in_string's "form" field which is a nested array
        [[{\"instance\": \"splunk_test\", \"address\": \"1.1.1.1\", \"port\": \"8081\"}", ""]]
        """
        is_nested = any(isinstance(i, list) for i in data)

        if is_nested:
            try:
                return json.loads(data[0][0])

            except (IndexError, json.decoder.JSONDecodeError) as e:
                return f"Could not parse data, make sure it is a valid JSON object. {e}"

    def format_error(self, error_msg, status_code):
        return {
            "payload": {
                "error": error_msg,
                "status": str(status_code)
            }
        }

    def handleStream(self, handle, in_string):
        """
        For future use
        """
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")
