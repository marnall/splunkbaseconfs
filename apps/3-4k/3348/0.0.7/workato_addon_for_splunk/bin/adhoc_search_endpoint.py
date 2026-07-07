import fix_path
import json
import time
from .base_handler import BaseRestHandler
from splunklib import results as results_lib
from .utils import workato_app_name
from .alert_action_utils import add_callback, remove_callback, has_workato_alert_action


class AdhocSearchHandler(BaseRestHandler):

    def handle_POST(self):
        payload = json.loads(self.request['payload'])
        s = self.create_service()

        # extract request parameters
        search_query = payload['search_query']
        earliest_time = payload['earliest_time']
        latest_time = payload[
            'latest_time'] if 'latest_time' in payload else 'now'

        # run the search
        result_stream = s.jobs.oneshot(search_query, earliest_time=earliest_time,
                                       latest_time=latest_time)
        results_reader = results_lib.ResultsReader(result_stream)

        # stream search results
        events = []
        messages = []
        for result in results_reader:
            if isinstance(result, results_lib.Message):
                messages.append({
                    "type": result.type,
                    "message": result.message,
                })
            elif isinstance(result, dict):
                events.append(result)

        # send response
        self.send_json_response({
            "results": events,
            "messages": messages,
        })
