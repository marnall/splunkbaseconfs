import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
lib_path = os.path.join(os.path.dirname(__file__), "..", "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
from base_handler import BaseRestHandler
import splunklib.results as results
from kubernetes_utility import K8SUtils


def update_stanza_urls(k8s, stanza):
    k8s_name = stanza["id"]
    for port_name in ["api", "jupyter", "tensorboard", "spark", "mlflow"]:
        attr_name = port_name + "_url"
        if attr_name not in stanza or not stanza[attr_name]:
            try:
                url = k8s.get_url(k8s_name, port_name)
            except:
                url = None
            if url:
                stanza.submit({
                    attr_name: url
                })
                stanza.refresh()


class SyncHandler(BaseRestHandler):
    # TODO actually it should be a POST handler
    def handle_GET(self):
        # get all container stanzas by ID
        stanza_by_container_id = dict()
        for stanza in self.container_stanzas:
            if "id" in stanza and stanza["id"]:
                container_id = stanza["id"]
                stanza_by_container_id[container_id] = stanza

        # get all running MLTK containers by ID
        docker_containers_by_id = dict()
        if self.is_docker_connected:
            containers = self.docker_client.containers.list(
                filters={
                    "label": "mltk_container"
                })
            for c in containers:
                docker_containers_by_id[c.id] = c

        # kill docker containers without matching config stanza
        for container_id, c in docker_containers_by_id.items():
            if not container_id in stanza_by_container_id:
                c.kill()

        # kill k8s containers without matching config stanza
        k8s_deployments_by_name = {}
        k8s = K8SUtils.from_service(self.service)
        if k8s:
            k8s_deployments_by_name = k8s.get_deployments_by_name()
            for container_id in k8s_deployments_by_name:
                if not container_id in stanza_by_container_id:
                    k8s.delete_deployment(container_id)

        # update config stanzas without matching (running) container
        for container_id, stanza in stanza_by_container_id.items():
            if stanza["id"]:
                if (stanza["cluster"] == "docker" and not container_id in docker_containers_by_id) \
                        or \
                        (stanza["cluster"] == "kubernetes" and not container_id in k8s_deployments_by_name):
                    stanza.submit({
                        "id": "",
                        "api_url": "",
                        "jupyter_url": "",
                        "tensorboard_url": "",
                        "spark_url": "",
                        "mlflow_url": ""
                    })
                    stanza.refresh()
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
                    del stanza_by_container_id[container_id]
                    if container_id in docker_containers_by_id:
                        c = docker_containers_by_id[container_id]
                        if c:
                            c.kill()
                    if container_id in k8s_deployments_by_name:
                        k8s.delete_deployment(container_id)

        if k8s:
            for _, stanza in stanza_by_container_id.items():
                k8s_name = stanza["id"]
                if k8s_name and stanza["cluster"] == "kubernetes":
                    update_stanza_urls(k8s, stanza)

        # TODO return last status
        self.send_json_response({})
