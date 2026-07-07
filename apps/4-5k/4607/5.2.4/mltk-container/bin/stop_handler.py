import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
lib_path = os.path.join(os.path.dirname(__file__), "..", "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
from base_handler import BaseRestHandler
from urllib.parse import parse_qs
from kubernetes_utility import K8SUtils


class StopHandler(BaseRestHandler):
    def handle_POST(self):
        params = parse_qs(self.request['payload'])
        model = params["model"][0] if "model" in params else ''

        stanza_name = "%s" % (model)
        stanza = self.container_stanzas[stanza_name]
        container_id = stanza["id"]
        cluster = stanza["cluster"]
        #self.get_logger().info("MLTKContainer STOP model name: %s - container_id: %s", model, container_id)

        if container_id:
            if cluster == "docker":
                c = self.docker_client.containers.get(container_id)
                c.stop()
            elif cluster == "kubernetes":
                k8s = K8SUtils.from_service(self.service)
                k8s.delete_deployment(container_id)
            self.get_logger().info("MLTKContainer STOP on cluster=%s model_name=%s container_id=%s", cluster, model, container_id)

        if "__dev__" in stanza_name:
            self.container_stanzas[stanza_name].submit({
                "id": "",
                "api_url": "",
                "jupyter_url": "",
                "tensorboard_url": "",
                "mlflow_url": "",
                "spark_url":""
            })
        else:
            self.container_stanzas[stanza_name].delete()

        self.send_json_response({})
