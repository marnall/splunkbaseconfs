import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
from base_handler import BaseRestHandler
from urllib.parse import parse_qs


class TransformersmodelHandler(BaseRestHandler):
    def handle_GET(self):
        self.get_logger().info("Transformersmodel handle_GET is called")
        entries = []
        for stanza in self.container_stanzas:
            if ("id" in stanza) and ("cluster" in stanza):
                container_id = stanza["id"]
                cluster = stanza["cluster"]

                base_path = "app/model/data"
                # tasks = ["summarization", "classification"]

                if container_id:
                    if cluster == "docker":
                        c = self.docker_client.containers.get(container_id)

                        ret_tasks = c.exec_run("/bin/bash -c \"cd {} && ls\"".format(base_path))
                        if ret_tasks is not None:
                            try:
                                assert ret_tasks.output.decode("utf-8").startswith('/bin/bash:') == False
                                tasks = list(filter(None, ret_tasks.output.decode("utf-8").split("\n")))
                            except:
                                tasks = None
                                e = {
                                    "container_name": stanza.name,
                                    "task": "0",
                                    "language": "0",
                                    "model": "0",
                                    "size": "0",
                                    "success": "0"
                                }
                                entries.append(e)

                            if tasks is not None:
                                for task in tasks:
                                    path = os.path.join(base_path, task)
                                    ret_langs = c.exec_run("/bin/bash -c \"cd {} && ls\"".format(path))
                                    if ret_langs is not None:
                                        try:
                                            assert ret_langs.output.decode("utf-8").startswith('/bin/bash:') == False
                                            langs = list(filter(None, ret_langs.output.decode("utf-8").split("\n")))
                                        except:
                                            langs = None
                                            e = {
                                                "container_name": stanza.name,
                                                "task": task,
                                                "language": "0",
                                                "model": "0",
                                                "size": "0",
                                                "success": "0"
                                            }
                                            entries.append(e)
                                        if langs is not None:
                                            for lang in langs:
                                                path = os.path.join(base_path, task, lang)
                                                ret_models = c.exec_run("/bin/bash -c \"cd {} && du -m\"".format(path))
                                                if ret_models is not None:
                                                    try:
                                                        assert ret_models.output.decode("utf-8").startswith('/bin/bash:') == False
                                                        models = list(filter(None, ret_models.output.decode("utf-8").split("\n")))
                                                        size_models = list()
                                                        for model in models:
                                                            r = model.split('\t')
                                                            r[-1] = r[-1].lstrip('./')
                                                            if r[-1] != '' and 'ipynb_checkpoints' not in r[-1] and len(r) == 2:
                                                                size_models.append(r)

                                                    except:
                                                        size_models = None
                                                        e = {
                                                            "container_name": stanza.name,
                                                            "task": task,
                                                            "language": lang,
                                                            "model": "0",
                                                            "size": "0",
                                                            "success": "0"
                                                        }
                                                    if size_models is not None:
                                                        for size_model in size_models:
                                                            e = {
                                                                "container_name": stanza.name,
                                                                "task": task,
                                                                "language": lang,
                                                                "model": size_model[-1],
                                                                "size": size_model[0],
                                                                "success": "1"
                                                            }
                                                            entries.append(e)

                    # elif cluster == "kubernetes":

                # self.get_logger().info("MLTKContainer retrieve info on cluster=%s model_name=%s container_id=%s", cluster, model, container_id)

        self.send_entries(entries)

    def handle_POST(self):
        self.get_logger().info("Transformersmodel handle_POST is called")
        base_path = "/srv/app/model/data"
        params = parse_qs(self.request['payload'])
        action = params["action"][0] if "action" in params else ''
        model = params["model"][0] if "model" in params else ''
        folder_path = params["target"][0] if "target" in params else "empty"

        stanza_name = "%s" % (model)
        stanza = self.container_stanzas[stanza_name]
        container_id = stanza["id"]
        cluster = stanza["cluster"]

        if action == "delete":
            if container_id:
                if cluster == "docker":
                    c = self.docker_client.containers.get(container_id)
                    try:
                        assert folder_path != "empty"
                        assert folder_path != ''
                        # path = os.path.join(base_path, folder_path)
                        path = base_path + folder_path
                        c.exec_run("/bin/bash -c \"rm -rf {}\"".format(path))
                        self.get_logger().info("Transformermodel handle_DELETE, deleted folder: {}".format(path))
                    except:
                        self.get_logger().info("Transformermodel handle_DELETE, no folder to delete")

        self.send_json_response({})
