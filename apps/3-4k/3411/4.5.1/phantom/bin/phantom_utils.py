
import json
from urllib.parse import quote_plus

# from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk import ResourceNotFound
import splunk.rest as rest

import ta_addonphantom_declare  # noqa: F401

import requests


def get_search_description(helper, search_name):
    path = f"/services/saved/searches/{quote_plus(search_name)}"
    try:
        response, contents = script_rest_helper(
            helper, helper.settings.get("session_key"), "GET", path
        )
        if 200 <= int(response.get("status")) < 300:
            json_content = json.loads(contents)
            entries = json_content.get("entry")
            for item in entries:
                if item.get("name", "") == search_name:
                    search_description = item.get("content", {}).get("description", "")
                    return search_description
    except Exception:
        pass
    return None


def script_rest_helper(logger, session_key, method, path, payload={}):
    try:
        args = {"method": method, "sessionKey": session_key}
        payload["output_mode"] = "json"
        if method == "POST" or method == "DELETE":
            args["postargs"] = payload
        else:
            args["getargs"] = payload
        response, contents = rest.simpleRequest(path, **args)
    except ResourceNotFound as e:
        # Not raising this error purposefully
        raise ResourceNotFound(f"ResourceNotFound: {e!s}")
    except Exception as e:
        # Not raising this error purposefully
        raise Exception(f"Exception: {e!s}")
    return response, contents


def rest_helper(logger, credentials, method, path, payload={}):
    try:
        request_func = getattr(requests, method)
    except AttributeError:
        return False, f"Invalid method: {method}"

    r = None
    try:
        r = request_func(
            path, auth=credentials, headers={"Content-Type": "application/json"}, verify=False
        )
    except Exception as e:
        return False, f"Error: {e}"

    try:
        return True, r.json()
    except Exception:
        return False, "Error: Could not parse json"
