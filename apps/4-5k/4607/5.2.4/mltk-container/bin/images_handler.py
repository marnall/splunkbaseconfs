import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
lib_path = os.path.join(os.path.dirname(__file__), "..", "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
from base_handler import BaseRestHandler


class ImagesHandler(BaseRestHandler):
    def handle_GET(self):
        # get all images stanzas by model name
        entries = []
        image_by_name = dict()
        for stanza in self.image_stanzas:
            image_by_name[stanza.name] = stanza
            if "image" in stanza:
                e = {
                    "name": stanza.name,
                    "image": stanza.image,
                    "repo": stanza.repo,
                    "title": stanza.title,
                    "runtime": stanza.runtime
                }
                entries.append(e)
        self.send_entries(entries)
