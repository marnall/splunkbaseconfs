"""Handle searching for IOCs.

This module is used to search for IOCs from the Recorded Future API.
"""

from recordedfuture.api.rfclient import RFClient


def search(in_dict, app_env):
    """Handle the search endpoint."""
    use_case = in_dict.get("path_info").split("/")[-1]
    data = dict(in_dict.get("query"))
    app_env.logger.debug("search params: %s", data)

    api = RFClient(app_env)
    res = api.search.search(use_case, json=data)

    return (200, {"links": {}, "entry": res})
