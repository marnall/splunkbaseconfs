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

class ConfigureHandler(BaseRestHandler):
    def handle_POST(self):
        params = parse_qs(self.request['payload'])
        docker_url = params["docker_url"][0] if "docker_url" in params else ''
        endpoint_hostname = params["endpoint_hostname"][0] if "endpoint_hostname" in params else ''
        endpoint_hostname_external = params["endpoint_hostname_external"][0] if "endpoint_hostname_external" in params else ''

        self.get_logger().info("docker_url: %s" % docker_url)
        self.get_logger().info("endpoint_hostname: %s" % endpoint_hostname)
        self.get_logger().info("endpoint_hostname_external: %s" % endpoint_hostname_external)

        if self.create_docker_client(docker_url).ping() == False:
            raise splunk.RESTException(400, "Could not ping Docker")

        self.service.confs["docker"]["connection"].submit({
            "docker_url": docker_url,
            "endpoint_hostname": endpoint_hostname,
            "endpoint_hostname_external": endpoint_hostname_external,
        })
        self.service.confs["app"]["install"].submit({
            "is_configured": 1,
        })
        self.service.apps["mltk-container-ja"].reload()

        self.send_json_response({})

    def handle_GET(self):
        docker_connection = self.service.confs["docker"]["connection"]
        self.send_json_response({
            "docker_url": docker_connection["docker_url"],
            "endpoint_hostname": docker_connection["endpoint_hostname"],
            "endpoint_hostname_external": docker_connection["endpoint_hostname_external"],
        })
