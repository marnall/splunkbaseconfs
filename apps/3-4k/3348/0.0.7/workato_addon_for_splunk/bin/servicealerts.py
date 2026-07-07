import fix_path
import json
from .base_handler import BaseRestHandler
from .utils import workato_app_name
from .alert_action_utils import get_callback_count

service_alert_name = 'IT Service Alerts'

class ServiceAlertsHandler(BaseRestHandler):
    def get_search(self):
        s = self.create_service()
        saved_searches = s.saved_searches
        search = saved_searches[service_alert_name]
        return search
    def handle_GET(self):
        search = self.get_search()
        self.send_json_response({
            "subscribed": get_callback_count(search) > 0,
            "is_scheduled": search.is_scheduled,
            "disabled": search.disabled,
        })
    def handle_POST(self):
        payload = json.loads(self.request['payload'])
        subscribe_response = self.call_json_service(
            "POST",
            "/services/workato/alerts",
            {
            "callback_url": payload["callback_url"],
            "search_name": service_alert_name
            }
        )
        search = self.get_search()
        if search.disabled:
            search.enable()
        self.send_json_response(subscribe_response)
    def handle_DELETE(self):
        payload = json.loads(self.request['payload'])
        unsubscribe_response = self.call_json_service(
            "DELETE",
            "/services/workato/alerts",
            payload
        )
        search = self.get_search()
        if get_callback_count(search)==0:
            search.disable()
        self.send_json_response(unsubscribe_response)
