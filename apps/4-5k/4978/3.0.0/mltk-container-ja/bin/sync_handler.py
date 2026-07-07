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
import splunklib.results as results

# TODO actually it should be a POST handler
class SyncHandler(BaseRestHandler):
    def handle_GET(self):
        # get all container stanzas by ID
        stanza_by_container_id = dict()
        for stanza in self.container_stanzas:
            if "id" in stanza and stanza["id"]:
                container_id = stanza["id"]
                stanza_by_container_id[container_id] = stanza

        # get all running MLTK containers by ID
        containers = self.docker_client.containers.list(
            filters={
                "label": "mltk_container"
            })
        containers_by_id = dict()
        for c in containers:
            containers_by_id[c.id] = c

        # kill containers without matching config stanza
        for container_id, c in containers_by_id.items():
            if not container_id in stanza_by_container_id:
                c.kill()

        # update config stanzas without matching (running) container
        for container_id, stanza in stanza_by_container_id.items():
            if stanza["id"]:
                if not container_id in containers_by_id:
                    stanza.submit({
                        "id": "",
                        "api_port": "",
                        "jupyter_port": "",
                        "tensorboard_port": "",
                    })

        # delete stanzas (and kill containers) without matching model
        # TODO listmodel can not retrieve private models from scheduled sync search 
        # permissions need to be set to fit ... into app:model_name
        # models with private (user) permission will not be available as own container but only be used with __dev__ 
        search_result = self.service.jobs.oneshot("| listmodels | search type=MLTKContainer sharing=global")
        search_result_reader = results.ResultsReader(search_result)
        models = [r for r in search_result_reader if isinstance(r, dict)]
        model_names = set([result["name"] for result in models])

        stanzas_to_delete = [
            stanza for stanza in self.container_stanzas
            if not stanza.name == "__dev__" and not stanza.name in model_names]
            
        for container_stanza in stanzas_to_delete:
            container_stanza.delete()
            if "id" in container_stanza:
                container_id = container_stanza["id"]
                if container_id:
                    if container_id in containers_by_id:
                        c = containers_by_id[container_id]
                        if c:
                            c.kill()


        # TODO return last status 
        self.send_json_response({})
