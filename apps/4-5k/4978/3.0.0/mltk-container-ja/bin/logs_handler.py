import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
docker_path = os.path.join(os.path.dirname(__file__),"dockerlib")
if docker_path not in sys.path:
    sys.path.insert(0, docker_path)
import json
import splunk
from base_handler import BaseRestHandler
from urllib.parse import parse_qs
import docker

class LogsHandler(BaseRestHandler):
    def handle_GET(self):
        stanza_name = "%s" % (self.pathParts[-1])
        entries = []
        if stanza_name in self.container_stanzas:
            container_id = self.container_stanzas[stanza_name]["id"]
            if container_id:
                c = self.docker_client.containers.get(container_id)            
                logs = c.logs(timestamps=True)
                logs = logs.decode('utf-8')
                for line in logs.split("\n"):
                    entries.append({
                        "_time":str(line[:30]),
                        "log":str(line[31:]),
                    })
        self.send_entries(entries)
