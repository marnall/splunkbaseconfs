import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
lib_path = os.path.join(os.path.dirname(__file__), "..", "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
from base_handler import BaseRestHandler
from kubernetes_utility import K8SUtils


class LogsHandler(BaseRestHandler):
    def handle_GET(self):
        stanza_name = "%s" % (self.pathParts[-1])
        entries = []
        if stanza_name in self.container_stanzas:
            stanza = self.container_stanzas[stanza_name]
            container_id = stanza["id"]
            cluster = stanza["cluster"]
            if container_id:
                if cluster == "docker":
                    c = self.docker_client.containers.get(container_id)
                    logs = c.logs(timestamps=True)
                    logs = logs.decode('utf-8')
                    for line in logs.split("\n"):
                        entries.append({
                            "_time": str(line[:30]),
                            "log": str(line[31:]),
                        })
                elif cluster == "kubernetes":
                    k8s = K8SUtils.from_service(self.service)
                    entries = k8s.get_logs(container_id)
        self.send_entries(entries)
