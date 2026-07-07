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
import sync_handler


class StatusHandler(BaseRestHandler):
    def handle_GET(self):
        # get all container stanzas by model name
        stanza_by_model = dict()
        for stanza in self.container_stanzas:
            stanza_by_model[stanza.name] = stanza

        # delete stanzas (and kill containers) without matching model
        search_result = self.service.jobs.oneshot("| listmodels | search type=MLTKContainer")
        search_result_reader = results.ResultsReader(search_result)
        models = [r for r in search_result_reader if isinstance(r, dict)]

        def create_entry(name):
            stanza = stanza_by_model[name]
            e = {}
            if 'id' in stanza and not stanza.id == None:
                if 'cluster' in stanza and not stanza.cluster == None:
                    e["cluster"] = stanza.cluster
                    if stanza.cluster == "kubernetes":
                        if not "api_url" in stanza or not stanza["api_url"]:
                            sync_handler.update_stanza_urls(self.service, stanza)
                if 'image' in stanza and not stanza.image == None:
                    e["image"] = stanza.image
                if 'api_url' in stanza and stanza.api_url:
                    e["api_url"] = stanza.api_url
                if 'jupyter_url' in stanza and stanza.jupyter_url:
                    e["jupyter_url"] = stanza.jupyter_url
                if 'tensorboard_url' in stanza and stanza.tensorboard_url:
                    e["tensorboard_url"] = stanza.tensorboard_url
                if 'spark_url' in stanza and stanza.spark_url:
                    e["spark_url"] = stanza.spark_url
                if 'mlflow_url' in stanza and stanza.mlflow_url:
                    e["mlflow_url"] = stanza.mlflow_url
                if 'runtime' in stanza and not stanza.runtime == None:
                    e["runtime"] = stanza.runtime
                if 'mode' in stanza and not stanza.mode == None:
                    e["mode"] = stanza.mode
            return e

        entries = []
        for m in models:
            name = m["name"]
            sharing = m["sharing"]
            e = {
                "model": name,
                "sharing": sharing
            }
            if name in stanza_by_model and sharing == "global":
                e.update(create_entry(name))
            entries.append(e)

        dev_model_name = "__dev__"
        if dev_model_name in stanza_by_model:
            e = {
                "model": dev_model_name,
                "sharing": "global"
            }
            e.update(create_entry(dev_model_name))
            entries.append(e)

        self.send_entries(entries)
