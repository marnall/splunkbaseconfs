import os
import sys
bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)
lib_path = os.path.join(os.path.dirname(__file__), "..", "lib")
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
from base_handler import BaseRestHandler

class AppHandler(BaseRestHandler):

    def handle_GET(self):
        try:
            response = self.service.confs["docker"]["connection"]["is_configured_complete"]
        except:
            response = "0"
        result = "1" if response=="1" else "0"
        self.send_json_response({"is_configured_complete": result})

