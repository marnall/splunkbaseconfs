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


class StartHandler(BaseRestHandler):
    def handle_POST(self):
        params = parse_qs(self.request['payload'])
        image = params["image"][0]
        model = params["model"][0] if "model" in params else ''
        runtime = params["runtime"][0] if "runtime" in params else None
        # platform specific and default hardcoded settings
        devFlag = model=="__dev__"        
        repo = "phdrieger/"
        image_name = "mltk-container-tf-cpu"
        tag = "latest"
        image_stanzas = dict()
        for stanza in self.image_stanzas:
            image_stanzas[stanza.image] = stanza
        if image in image_stanzas:
            image_stanza = image_stanzas[image]
            repo = image_stanza.repo
            image_name = image_stanza.image

        self.get_logger().info("MLTKContainer START model name: %s", image+"::"+repo+"::"+image_name)

        # TODO fixed to port 8888 and 6006 for cloud instance testing - change to None again later!
        c = self.docker_client.containers.run(repo+image_name,labels={
            "mltk_container": "",
            "mltk_model": model,
        }, runtime=runtime, detach=True, ports={
            '8888/tcp': '8888' if devFlag else None,
            '6006/tcp': '6006' if devFlag else None,
            '5000/tcp': None,
        }, volumes={
            'mltk-container-app': {'bind': '/srv/app', 'mode': 'rw'},
            'mltk-container-notebooks': {'bind': '/srv/notebooks', 'mode': 'rw'}
        },remove=True)

        inspect = self.docker_api_client.inspect_container(c.id)

        stanza_name = "%s" % (model)
        if not stanza_name in self.container_stanzas:
            container_stanza = self.container_stanzas.create(stanza_name)
        else:
            container_stanza = self.container_stanzas[stanza_name]
        container_stanza.submit({
            "id": c.id,
            "image": image_name,
            "runtime": runtime,
            "api_port": inspect["NetworkSettings"]["Ports"]['5000/tcp'][0]["HostPort"],
            "jupyter_port": inspect["NetworkSettings"]["Ports"]['8888/tcp'][0]["HostPort"],
            "tensorboard_port": inspect["NetworkSettings"]["Ports"]['6006/tcp'][0]["HostPort"],
        })

        self.send_json_response({
            "container_id": c.short_id,
        })
