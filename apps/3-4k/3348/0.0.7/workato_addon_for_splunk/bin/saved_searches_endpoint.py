import fix_path
import json
import time
from .base_handler import BaseRestHandler
from splunklib import results as results_lib
from .utils import workato_app_name
from .alert_action_utils import add_callback, remove_callback, has_workato_alert_action


class SavedSearchesHandler(BaseRestHandler):

    def handle_GET(self):
        s = self.create_service()
        saved_searches = s.saved_searches.list(search="is_scheduled=0")

        def filter(search):
            if search.access.app == workato_app_name:
                return False
            if search.name.startswith("__"):
                return False
            return True
        self.send_json_response(
            [search.name for search in saved_searches if filter(search)]
        )

    def handle_POST(self):
        payload = json.loads(self.request['payload'])
        s = self.create_service()

        # extract request parameters
        saved_search = s.saved_searches[payload['search_name']]

        # build search query
        search_query = "savedsearch \"%s\"" % saved_search.name

        # run the search
        result_stream = s.jobs.oneshot(search_query)
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
