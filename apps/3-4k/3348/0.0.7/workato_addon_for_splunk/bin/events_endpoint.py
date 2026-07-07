import fix_path
import json
from .base_handler import BaseRestHandler
from .utils import workato_app_name
from .alert_action_utils import add_callback, remove_callback, has_workato_alert_action

class EventsHandler(BaseRestHandler):
    def handle_POST(self):
        payload = json.loads(self.request['payload'])
        message = payload['payload']
        index = payload['index'] if 'index' in payload else 'main'
        source = payload['source'] if 'source' in payload else None
        sourcetype = payload['sourcetype'] if 'sourcetype' in payload else None
        host = payload['host'] if 'host' in payload else None
        s = self.create_service()
        index = s.indexes[index]
        index.submit(message, host=host, source=source, sourcetype=sourcetype)
        self.send_json_response({})
