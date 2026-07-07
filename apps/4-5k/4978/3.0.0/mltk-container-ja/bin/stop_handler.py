import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
docker_path = os.path.join(os.path.dirname(__file__),"dockerlib")
if docker_path not in sys.path:
    sys.path.insert(0, docker_path)
import splunk
import json
from base_handler import BaseRestHandler
from urllib.parse import parse_qs
import docker

class StopHandler(BaseRestHandler):
    def handle_POST(self):
        params = parse_qs(self.request['payload'])
        model = params["model"][0] if "model" in params else ''

        stanza_name = "%s" % (model)
        container_id = self.container_stanzas[stanza_name]["id"]

        if container_id:
            c = self.docker_client.containers.get(container_id)
            c.stop()

        if "__dev__" in stanza_name:
            self.container_stanzas[stanza_name].submit({
                "id": "",
                "api_port": "",
                "jupyter_port": "",
                "tensorboard_port": "",
            })
        else:
            self.container_stanzas[stanza_name].delete()

        self.send_json_response({})
