import json
import os
import sys
import time
import uuid

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from spl_gen.constants import SAVED_SEARCH_SEARCH_LOGS
from spl_gen.remote.v1alpha1 import SaiaApi
from spl_gen.utils import log_kwargs, reset_saved_search_time
from splunklib.searchcommands import Configuration, EventingCommand, dispatch


@Configuration()
class SubmitSearchLogsCommand(EventingCommand):
    def is_valid_search(self, search: str):
        try:
            parsed_search = search.strip("'")
            response = self.service.parse(parsed_search, output_mode="json")
            response_body = response["body"].read()
            decoded_body = json.loads(response_body.decode("utf-8"))

            return response["status"] == 200 and bool(decoded_body["commands"])
        except Exception:
            return False

    def transform(self, records):
        # system_scoped_service is same as self.service since this command should only get
        # run by the splunk_system_role as a part of the search logs saved search
        # Search log upload still uses the v1 data contract, so keep v1 hardcoded here.
        api = SaiaApi(
            service=self.service,
            system_scoped_service=self.service,
            username=self.metadata.searchinfo.username,
        )  # pyright: ignore
        self.logger.info("Submitting search logs")

        searches = []
        for record in records:
            search = record["search"]
            # TODO: make sure this function actually filters out the valid searches
            if self.is_valid_search(search):
                roles = []
                if record["roles"]:
                    roles = record["roles"].split()
                searches.append({"user": record["user"], "spl": search, "roles": roles})

        request_id = str(uuid.uuid4())
        self.logger.info(
            log_kwargs(request_id=request_id, anticipated_entry_count=len(searches))
        )

        try:
            api.submit_user_search_logs(searches=searches, request_id=request_id)
            self.logger.info("Search logs submission successful")
            result = "successful"
            reset_saved_search_time(self.service, SAVED_SEARCH_SEARCH_LOGS)
        except requests.RequestException as ex:
            self.logger.error(f"Search logs POST failed: {ex.response.text}")
            result = "unsuccessful"

        yield {"_time": time.time(), "result": result}


dispatch(SubmitSearchLogsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
