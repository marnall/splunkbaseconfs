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


class ImagesHandler(BaseRestHandler):
    def handle_GET(self):
        # get all images stanzas by model name
        entries = []
        image_by_name = dict()
        for stanza in self.image_stanzas:
            image_by_name[stanza.name] = stanza
            e = {
                "name": stanza.name,
                "image": stanza.image,
                "repo": stanza.repo,
                "title": stanza.title,
                "runtime": stanza.runtime
            }
            entries.append(e)
        self.send_entries(entries)
