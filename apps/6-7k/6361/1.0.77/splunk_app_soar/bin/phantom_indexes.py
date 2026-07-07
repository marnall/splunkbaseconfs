# Copyright (C) 2023-2024 Splunk Inc. All Rights Reserved.

# Remote Search
import os
import sys
import json

from splunk.persistconn.application import PersistentServerConnectionApplication

APP_HOME_DIR = os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", "splunk_app_soar")

sys.path.insert(0, os.path.join(APP_HOME_DIR, "bin"))
from soar_utils import setup_logging, rest_helper, pretty_form_map

ENDPOINT_INDEXES = "/services/data/indexes"
INDEXES_CONF = "/servicesNS/nobody/splunk_app_soar/configs/conf-indexes"


class PhantomIndexes(PersistentServerConnectionApplication):
    """
    POST: parameter 'indexes' (list): list of indexes for a given Phantom instance
        returns: status code, error if applicable
        Add indexes to Splunk that are not already included
        Example: curl -ku admin:password https://127.0.0.1:8089/services/phantom_indexes -d '{"indexes": ["phantom_1_container", "phantom_1_artifacts"]}'
    """

    def __init__(self, command_line, command_arg):
        self.log = None
        self.session_key = None
        PersistentServerConnectionApplication.__init__(self)

    def handle_post(self, form_data):
        self.log.info("Indexes from Phantom: {}".format(form_data))
        # Get the current phantom indexes
        phantom_indexes = list()
        try:
            payload = {"search": "phantom_", "count": 0}
            response, contents = rest_helper(self, "GET", ENDPOINT_INDEXES, payload)
            contents = json.loads(contents) if type(contents) == 'str' else contents
            for item in contents.get("entry", []):
                phantom_indexes.append(item.get("name"))
            self.log.info("Current phantom indexes: {}".format(phantom_indexes))
        except Exception as e:
            self.log.error("Error retrieving current indexes: {}".format(e))
            return False, "Error retrieving current indexes"

        # Add the indexes that are not yet in Splunk
        indexes_added = False
        if form_data:
            for item in form_data:
                if item not in phantom_indexes:
                    payload = {
                        "name": item,
                        "homePath": f"$SPLUNK_DB/{item}/db",
                        "coldPath": f"$SPLUNK_DB/{item}/colddb",
                        "thawedPath": f"$SPLUNK_DB/{item}/thaweddb",
                        "disabled": 0
                    }
                    try:
                        response, contents_json = rest_helper(
                            self, "POST", INDEXES_CONF, payload
                        )
                        self.log.info("Saved new index '{}'".format(item))
                        indexes_added = True
                    except Exception as e:
                        self.log.error("Error saving '{}'".format(item))
            if indexes_added is True:
                return True, "New indexes added"
            else:
                return True, "No new indexes added"
        else:
            return True, "No indexes were supplied"

    def handle(self, args):
        request = json.loads(args)
        method = request["method"]
        self.log = setup_logging("phantom_remote_search_indexes.log", method)
        self.session_key = request["session"]["authtoken"]

        ret_val, content = False, None

        if method == "POST":
            form = request.get("form", [])
            form = pretty_form_map(self, form)
            form = json.loads(form).get("indexes", [])
            ret_val, content = self.handle_post(form)

        if ret_val is True:
            result = {"success": True, "status": 200, "response": content}
        else:
            result = {"success": False, "status": 400, "error": content}

        return json.dumps({"payload": result})
