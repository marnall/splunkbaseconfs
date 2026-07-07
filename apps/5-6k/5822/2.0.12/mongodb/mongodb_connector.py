# File: mongodb_connector.py
#
# Copyright (c) 2018-2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
#
# phantom imports
import json

import phantom.app as phantom
import requests

# NOTE: These two imports may cause pylint to crash on this file
from bson.json_util import dumps as bson_dumps, loads as bson_loads
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

import pymongo


class RetVal(tuple):
    def __new__(cls, val1, val2=None):
        return tuple.__new__(RetVal, (val1, val2))


class MongodbConnector(BaseConnector):
    def __init__(self):
        super().__init__()
        self._state = None
        self._client = None
        self._db = None
        self._db_name = None

    def _encode_to_json_dict(self, data):
        # Convert BSON -> JSON dict
        return json.loads(bson_dumps(data))

    def _check_collection(self, action_result, collection):
        # Check to see if a collection already exists
        # MongoDB wont throw an error if using a collection that doesn't exist,
        #  but we want to create one if an unknown collection is used
        #  in a get, update, or delete
        collections = self._db.collection_names(include_system_collections=False)
        if collection not in collections:
            return action_result.set_status(phantom.APP_ERROR, "Specified collection does not exist")
        return phantom.APP_SUCCESS

    def _handle_test_connectivity(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))

        self.save_progress("Test connection to MongoDB server...")
        try:
            self._client.admin.command("ismaster")
        except Exception as e:
            self.save_progress("Test connectivity failed")
            return action_result.set_status(phantom.APP_ERROR, "Unable to establish connection to MongoDB server", e)

        self.save_progress("Getting db names")
        try:
            db_names = self._client.database_names()
        except Exception as e:
            self.save_progress("Test connectivity failed")
            return action_result.set_status(phantom.APP_ERROR, "Error listing databases", e)

        if self._db_name not in db_names:
            # The DB will be created after a 'post data' action
            self.save_progress("Warning: specified database not found in MongoDB")

        self.save_progress("Test connectivity passed")
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_post_data(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        collection = param["collection"]
        try:
            data = bson_loads(param["data"])
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Unable to load data", e)
        self.save_progress("Inserting data...")
        if isinstance(data, list):
            add_method = self._db[collection].insert_many
        elif isinstance(data, dict):
            add_method = self._db[collection].insert_one
        else:
            return action_result.set_status(phantom.APP_ERROR, "Unable to post data, must be either dict or list")

        try:
            result = add_method(data)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Unable to add to database", e)

        try:
            # See if result is from insert_one
            action_result.add_data(self._encode_to_json_dict({"_id": result.inserted_id}))
        except AttributeError:
            # This is a result from insert_many
            for obj in result.inserted_ids:
                action_result.add_data(self._encode_to_json_dict({"_id": obj}))

        # Here _id will be set to an ObjectID object if one is not explicitly set
        # Regardless of the shape of _id, grabbing the data at
        #  action_result.data.*._id will always get the correct thing to use in future queries

        return action_result.set_status(phantom.APP_SUCCESS, "Successfully added to database")

    def _handle_get_data(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        collection = param["collection"]
        query = param.get("filter")
        if query:
            try:
                query = bson_loads(query)
            except Exception as e:
                return action_result.set_status(phantom.APP_ERROR, "Unable to load filter", e)

        ret_val = self._check_collection(action_result, collection)
        if phantom.is_fail(ret_val):
            return ret_val
        self.save_progress("Fetching data...")
        query_results = self._db[collection].find(query)
        for result in query_results:
            try:
                action_result.add_data(self._encode_to_json_dict(result))
            except Exception as e:
                return action_result.set_status(phantom.APP_ERROR, "Error serializing query results", e)

        try:
            record_count = query_results.count()
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Error returning record count from query", e)

        action_result.update_summary({"total_records": record_count, "message": "Successfully got data"})
        return action_result.set_status(phantom.APP_SUCCESS)

    def _handle_delete_data(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        collection = param["collection"]
        query = param["filter"]
        try:
            query = bson_loads(query)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Unable to load filter", e)
        self.save_progress("Deleting data...")
        try:
            results = self._db[collection].delete_many(query)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Error deleting data", e)

        ret_val = self._check_collection(action_result, collection)
        if phantom.is_fail(ret_val):
            return ret_val

        summary = action_result.get_summary()
        summary["deleted_count"] = results.deleted_count
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully deleted data")

    def _handle_update_data(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        collection = param["collection"]
        data = param["update"]
        query = param["filter"]

        try:
            data = bson_loads(data)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Unable to load data", e)

        try:
            query = bson_loads(query)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Unable to load filter", e)

        ret_val = self._check_collection(action_result, collection)
        if phantom.is_fail(ret_val):
            return ret_val
        self.save_progress("Updating data...")
        try:
            results = self._db[collection].update_many(query, data)
        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, "Error updating data", e)

        summary = action_result.get_summary()
        summary["modified_count"] = results.modified_count
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully updated data")

    def _handle_list_tables(self, param):
        action_result = self.add_action_result(ActionResult(dict(param)))
        self.save_progress(f"In action handler for: {self.get_action_identifier()}")
        self.save_progress("Fetching data...")
        collections = self._db.collection_names(include_system_collections=False)
        for collection in collections:
            action_result.add_data({"collection": collection})
        return action_result.set_status(phantom.APP_SUCCESS, "Successfully listed collections")

    def handle_action(self, param):
        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == "test_connectivity":
            ret_val = self._handle_test_connectivity(param)

        elif action_id == "post_data":
            ret_val = self._handle_post_data(param)

        elif action_id == "get_data":
            ret_val = self._handle_get_data(param)

        elif action_id == "update_data":
            ret_val = self._handle_update_data(param)

        elif action_id == "delete_data":
            ret_val = self._handle_delete_data(param)

        elif action_id == "list_tables":
            ret_val = self._handle_list_tables(param)

        return ret_val

    def initialize(self):
        self._state = self.load_state()
        config = self.get_config()
        host = config["host"]
        self._db_name = config["database"]
        username = config.get("username")
        password = config.get("password")
        auth_fields = config.get("auth_fields")
        if auth_fields:
            try:
                auth_fields_dict = json.loads(auth_fields)
            except Exception as e:
                self.save_progress(str(e))
                return phantom.APP_ERROR
        else:
            auth_fields_dict = {}

        try:
            self._client = pymongo.MongoClient(host, username=username, password=password, **auth_fields_dict)
            self._db = self._client[self._db_name]
        except Exception as e:
            self.save_progress(str(e))
            return phantom.APP_ERROR
        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved accross actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


def main():
    import argparse
    import sys

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument("input_test_json", help="Input Test JSON file")
    argparser.add_argument("-u", "--username", help="username", required=False)
    argparser.add_argument("-p", "--password", help="password", required=False)
    argparser.add_argument("-v", "--verify", action="store_true", help="verify", required=False, default=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify
    timeout = 30

    if username is not None and password is None:
        # User specified a username but not a password, so ask
        import getpass

        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = MongodbConnector._get_phantom_base_url() + "/login"

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=timeout)
            csrftoken = r.cookies["csrftoken"]

            data = dict()
            data["username"] = username
            data["password"] = password
            data["csrfmiddlewaretoken"] = csrftoken

            headers = dict()
            headers["Cookie"] = "csrftoken=" + csrftoken
            headers["Referer"] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, verify=verify, data=data, headers=headers, timeout=timeout)
            session_id = r2.cookies["sessionid"]
        except Exception as e:
            print("Unable to get session id from the platform. Error: " + str(e))
            sys.exit(1)

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = MongodbConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json["user_session_token"] = session_id
            connector._set_csrf_info(csrftoken, headers["Referer"])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit(0)


if __name__ == "__main__":
    main()
