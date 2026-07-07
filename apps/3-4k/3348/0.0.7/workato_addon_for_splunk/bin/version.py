import fix_path
from .base_handler import BaseRestHandler
import json
from .utils import workato_app_name

class VersionHandler(BaseRestHandler):
    def handle_GET(self):
        s = self.create_service()
        self.send_json_response({
            "splunk_version": s.info["version"],
            "itsi_version": s.apps['itsi'].version if 'itsi' in s.apps else "",
            "es_version": s.apps['SplunkEnterpriseSecuritySuite'].version if 'SplunkEnterpriseSecuritySuite' in s.apps else "",
            "workato_version": s.apps[workato_app_name].version if workato_app_name in s.apps else "",
        })
