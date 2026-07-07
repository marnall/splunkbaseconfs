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


class StatusHandler(BaseRestHandler):
    def handle_GET(self):
        endpoint_hostname = self.connection["endpoint_hostname"]
        endpoint_hostname_external = self.connection["endpoint_hostname_external"]
        if endpoint_hostname_external==None:
            endpoint_hostname_external = endpoint_hostname
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
            if 'id' in stanza and not stanza.id==None:
                if 'image' in stanza and not stanza.image==None:
                    e["image"] = stanza.image
                if 'api_port' in stanza and not stanza.api_port==None:
                    e["api_url"] = "http://%s:%s" % (endpoint_hostname, stanza.api_port)
                if 'jupyter_port' in stanza and not stanza.jupyter_port==None:
                    e["jupyter_url"] = "http://%s:%s" % (endpoint_hostname_external, stanza.jupyter_port)
                if 'tensorboard_port' in stanza and not stanza.tensorboard_port==None:
                    e["tensorboard_url"] = "http://%s:%s" % (endpoint_hostname_external, stanza.tensorboard_port)
                if 'runtime' in stanza and not stanza.runtime==None:
                    e["runtime"] = stanza.runtime
            return e

        entries = []
        for m in models:
            name = m["name"]
            sharing = m["sharing"]
            e = {
                "model": name,
                "sharing": sharing
            }
            if name in stanza_by_model and sharing=="global":
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
