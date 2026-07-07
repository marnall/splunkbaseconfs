import os
import sys
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import dependency_handler  # noqa: F401  # Do not delete

from libs.base_objects.custom_splunk_endpoint_base import CustomSplunkEndpointBase


class CustomSearchHandler(
    CustomSplunkEndpointBase, PersistentServerConnectionApplication
):
    """The only class inheriting from PersistentServerConnectionApplication"""

    def __init__(self, command_line, command_arg, logger=None):
        PersistentServerConnectionApplication.__init__(self)
        CustomSplunkEndpointBase.__init__(self)

    def process_payload(self, payload):
        """Process the payload by constructing and executing a search query."""
        search_query = self._get_search_query(payload)
        response = self._query_splunk(search_query)
        return self._create_response("Successfully retrieved results", 200, response)

    def _get_search_query(self, payload):
        """Retrieve the search query from the payload."""
        query_values = payload.get("query", [])
        for query in query_values:
            if query[0] == "query":
                return query[1]
        raise ValueError("No search query found in the payload")
