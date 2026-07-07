import fix_path
import json
from .base_handler import BaseRestHandler
from .utils import workato_app_name
from .alert_action_utils import add_callback, remove_callback, has_workato_alert_action

class AlertsHandler(BaseRestHandler):
    def handle_GET(self):
        s = self.create_service()
        saved_searches = s.saved_searches.list(search="is_scheduled=1")
        def filter(search):
            if search.access.app==workato_app_name:
                return False
            if search.name.startswith("__"):
                return False
            return has_workato_alert_action(search)
        self.send_json_response(
            [ search.name for search in saved_searches if filter(search) ]
        )
    def handle_POST(self):
        payload = json.loads(self.request['payload'])
        s = self.create_service()
        saved_search = s.saved_searches[payload['search_name']]
        add_callback(saved_search, payload['callback_url'])
        self.send_json_response({
            "search_name": payload['search_name'],
            "callback_url": payload['callback_url'],
        })
    def handle_DELETE(self):
        payload = json.loads(self.request['payload'])
        s = self.create_service()
        saved_search = s.saved_searches[payload['search_name']]
        remove_callback(saved_search, payload['callback_url'])
        self.send_json_response({})
