# File: phantom_splunk.py
# Copyright (c) 2016-2025 Splunk Inc.
#
# SPLUNK CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Splunk Inc. is PROHIBITED.

import hashlib
import json
import time
from traceback import format_exc
from urllib.parse import quote, urlencode

import splunk

import ta_addonphantom_declare  # noqa: F401

import cherrypy


ENDPOINT_COLLECTION_DATA = "/servicesNS/nobody/phantom/storage/collections/data"
PASSWORD_ENDPOINT = "/servicesNS/nobody/phantom/storage/passwords"
DATA_MODELS_ENDPOINT = "/servicesNS/nobody/phantom/datamodel/model"
SAVED_SEARCHES_ENDPOINT = "/servicesNS/nobody/phantom/saved/searches/"
SAVED_SEARCHES_PH_GET_ENDPOINT = "/servicesNS/nobody/phantom/saved/searches?search=eai%3Aacl.app%3Dphantom&output_mode=json&offset=120"
AD_HOC_SEARCH_ENDPOINT = "/services/search/v2/jobs/export"
WORKBOOKS_ENDPOINT = "/servicesNS/nobody/phantom/phantom_workbooks"
SERVER_INFO_ENDPOINT = "/services/server/info"
SERVER_SETTINGS_ENDPOINT = "/services/server/settings"
CONFIG_ENDPOINT = "/servicesNS/nobody/phantom/configs/conf-phantom"
APP_NAME = "phantom"
OWNER = "nobody"


class PasswordStoreException(Exception):
    pass


class Splunk:
    def __init__(self, session, logger):
        self.session = session
        if not self.session:
            try:
                self.session = cherrypy.session.get("sessionKey")
            except Exception:
                pass
        self.hostname = None
        self.logger = logger
        # self.clear_password_from_store()

    def get_passwords(self):
        content = {}
        try:
            response, content = self.get(PASSWORD_ENDPOINT)
        except Exception:
            self.logger.error("Could not retrieve passwords from storage")

        ids = [pass_id["content"]["username"] for pass_id in content["entry"]]  # current passwords
        return ids

    def delete_password(self, pw_id):
        path = f"{PASSWORD_ENDPOINT}/%3A{pw_id}%3A"
        try:
            args = {
                "method": "DELETE",
                "sessionKey": self.session,
                "postargs": {"output_mode": "json"},
            }
            response, content = splunk.rest.simpleRequest(path, **args)
            self.logger.info(f"Delete password '{pw_id}': {response.status}")
        except Exception as e:
            self.logger.error(f"Could not delete '{pw_id}': {e}")

    def update_password(self, name, token):
        pw_id = hashlib.sha1(name.encode()).hexdigest()
        path = f"{PASSWORD_ENDPOINT}/%3A{pw_id}%3A"
        try:
            args = {
                "method": "POST",
                "sessionKey": self.session,
                "postargs": {"output_mode": "json", "password": token},
            }
            response, content = splunk.rest.simpleRequest(path, **args)
            self.logger.debug(f"Posting password ID '{pw_id}': {response.status}")
        except Exception as e:
            self.logger.error(f"Could not post '{pw_id}': {e}")

    def clear_password_from_store(self):
        content = {}
        try:
            response, content = self.get(PASSWORD_ENDPOINT)
        except Exception:
            self.logger.error("Could not retrieve passwords from storage")

        ids = [pass_id["links"]["remove"] for pass_id in content["entry"]]
        for i in ids:
            self.logger.debug(f"Attempting to clear id '{i}' from password store")
            try:
                args = {
                    "method": "DELETE",
                    "sessionKey": self.session,
                    "postargs": {"output_mode": "json"},
                }
                response, content = splunk.rest.simpleRequest(i, **args)
            except Exception:
                self.logger.error(f"Could not delete '{i}' from password store")

        try:
            response, content = self.get(PASSWORD_ENDPOINT)
            ids = [pass_id["id"] for pass_id in content["entry"]]
        except:
            self.logger.error("Could not retrieve passwords from storage")

    def update_workbook(self, name, value):
        path = f"{CONFIG_ENDPOINT}/workbooks"
        data = {f"{name}": value}
        return self.post(path, params=data)

    def get(self, path, params=None):
        if params is None:
            params = {}
        success, content = self.rest(path, params, method="GET")
        content = json.loads(content)
        return success, content

    def post(self, path, params=None):
        if params is None:
            params = {}
        success, content = self.rest(path, params, method="POST")
        content = json.loads(content)
        return success, content

    def delete(self, path, params=None):
        if params is None:
            params = {}
        success, content = self.rest(path, params, method="DELETE")
        content = json.loads(content)
        return success, content

    def rest_kv(self, path, payload, method):
        success = False
        try:
            path = quote(path)
            payload["output_mode"] = "json"
            args = {
                "method": method,
                "sessionKey": self.session,
            }
            if method == "POST" or method == "DELETE":
                args["jsonargs"] = json.dumps(payload)
            else:
                args["getargs"] = payload
            response, content = splunk.rest.simpleRequest(path, **args)
            success = 200 <= int(response.get("status")) < 300
            if not success:
                raise Exception("status code {}: {}".format(response.get("status"), content))
        except splunk.AuthorizationFailed as e:
            self.logger.error(format_exc())
            raise splunk.AuthorizationFailed(f"Error talking to Splunk: {method} {path}: {e!s}")
        except Exception as e:
            # self.logger.error(format_exc()) removing this since it causes benign errors to show up in the logs.
            raise Exception(f"Error talking to Splunk: {method} {path}: {e!s}")
        # self.logger.info([success, content])
        return success, content

    def rest(self, path, payload, method):
        success = False
        try:
            path = quote(path)
            # self.logger.info([path, payload])
            payload["output_mode"] = "json"
            args = {
                "method": method,
                "sessionKey": self.session,
            }
            if method == "POST" or method == "DELETE":
                args["postargs"] = payload
            else:
                args["getargs"] = payload
            self.logger.info(f"{method} {path} with payload")
            response, content = splunk.rest.simpleRequest(path, **args)
            # self.logger.info([response, content])
            success = 200 <= int(response.get("status")) < 300
            if not success:
                raise Exception("status code {}: {}".format(response.get("status"), content))
        except splunk.AuthorizationFailed as e:
            self.logger.error(format_exc())
            raise splunk.AuthorizationFailed(f"Error talking to Splunk: {method} {path}: {e!s}")
        except Exception as e:
            # self.logger.error(format_exc()) removing this since it causes benign errors to show up in the logs.
            raise Exception(f"Error talking to Splunk: {method} {path}: {e!s}")
        # self.logger.info([success, content])
        return success, content

    def load_auth_token(self, server):
        if not server:
            return ""

        name = hashlib.sha1(server.encode()).hexdigest()

        try:
            succeeded, result = self.get(f"{PASSWORD_ENDPOINT}/{name}")
            return result.get("entry", [{}])[0].get("content", {}).get("clear_password")
        except Exception:
            self.logger.exception("Error: could not load auth token from storage")
        return None

    def save_auth_token(self, name, token):
        name = hashlib.sha1(name.encode()).hexdigest()
        try:
            success, content = self.get(f"{PASSWORD_ENDPOINT}/{name}")
        except:
            try:
                args = {
                    "name": name,
                    "password": token,
                }
                self.post(PASSWORD_ENDPOINT, args)
            except splunk.AuthorizationFailed:
                raise
            except Exception as e:
                self.logger.error(format_exc())
                raise PasswordStoreException(str(e))

    def get_data_models(self):
        offset = 0
        args = {
            "output_mode": "json",
            "offset": offset,
        }

        models = {}
        while True:
            response, content = splunk.rest.simpleRequest(
                DATA_MODELS_ENDPOINT, method="GET", sessionKey=self.session, getargs=args
            )
            if response["status"] != "200":
                raise Exception(content)
            content = json.loads(content)
            entries = content["entry"]
            paging = content.get("paging", {})
            for entry in entries:
                desc = entry.get("content", {}).get("description", "{}")
                searches = json.loads(desc)
                name = searches.get("modelName")
                if not name:
                    continue
                models[name] = model = {}
                for o in searches["objects"]:
                    model[o["objectName"]] = search = {"prefixes": {}}
                    search["fields"] = fields = []
                    for f in o.get("fields", []):
                        if f.get("type") != "objectCount":
                            field_name = f.get("fieldName")
                            fields.append(field_name)
                            search["prefixes"][field_name] = f.get("owner", "")
                    for c in o.get("calculations", []):
                        for f in c.get("outputFields", []):
                            field_name = f.get("fieldName")
                            fields.append(field_name)
                            search["prefixes"][field_name] = f.get("owner", "")
            if (paging.get("offset", 0) + len(entries)) < paging.get("total", 0):
                offset += len(entries)
                args["offset"] = offset
            else:
                break
        # self.logger.info(str(models))
        return models

    def get_saved_searches(self, search_name):
        offset = 0
        args = {"output_mode": "json", "offset": offset, "count": 0}
        searches = {}
        while True:
            response, content = splunk.rest.simpleRequest(
                SAVED_SEARCHES_ENDPOINT + "/" + quote(search_name, safe=""),
                method="GET",
                sessionKey=self.session,
                getargs=args,
            )
            if response["status"] != "200":
                raise Exception(content)
            content = json.loads(content)
            entries = content["entry"]
            paging = content.get("paging", {})
            for entry in entries:
                if entry.get("content", {}).get("action.script.filename") != "phantom_forward.py":
                    searches[entry["name"]] = None
            if (paging.get("offset", 0) + len(entries)) < paging.get("total", 0):
                offset += len(entries)
                args["offset"] = offset
            else:
                break
        # self.logger.info(searches)
        return searches

    def save_savedsearch(self, info, is_new_seaerch):
        name = info["name"]
        path = f"{SAVED_SEARCHES_ENDPOINT}/{name}"
        # Remove 'name' from info if it exists, as it is not a valid parameter for the POST request
        if not is_new_seaerch and "name" in info:
            del info["name"]
        response = self.post(path, info)
        try:
            self.post(
                f"{SAVED_SEARCHES_ENDPOINT}/{name}/acl", {"sharing": "global", "owner": "nobody"}
            )
        except Exception:
            self.logger.warning(f'Failed to set sharing=global on saved search "{name}"')
        return response

    def delete_saved_search(self, search_name):
        if not search_name and search_name.strip():
            return
        content = self.get_savedsearch(search_name, SAVED_SEARCHES_PH_GET_ENDPOINT)
        entries = content.get("entry", [])
        if not entries:
            return
        for item in entries:
            if item.get("name") == search_name:
                entry = item
                if entry.get("content", {}).get("action.script.filename") != "phantom_forward.py":
                    self.logger.warning(
                        f"Not deleting {search_name}, does not appear to be our own search"
                    )
                    return
        path = SAVED_SEARCHES_ENDPOINT
        path += search_name

        try:
            success, content = self.rest(path, {}, method="GET")
        except Exception:
            self.logger.debug(f"'{search_name}' does not exist in {SAVED_SEARCHES_ENDPOINT}")
            # self.logger.debug("Error: {}".format(str(e)))
            return

        if success:
            self.rest(path, {}, "DELETE")

    def get_savedsearch(self, search_name, app_endpoint=None):
        endpoint = SAVED_SEARCHES_ENDPOINT + "/" + quote(search_name, safe="")
        if app_endpoint:
            endpoint = app_endpoint
        args = {"output_mode": "json", "count": 0}
        try:
            response, content = splunk.rest.simpleRequest(
                endpoint, method="GET", sessionKey=self.session, getargs=args
            )
        except Exception:
            self.logger.debug(f"'{search_name}' does not yet exist in {SAVED_SEARCHES_ENDPOINT}")
            return {}
        if response["status"] != "200":
            raise Exception(content)
        # self.logger.info(content)
        content = json.loads(content)
        return content

    def search(self, info):
        success, content = self.rest(AD_HOC_SEARCH_ENDPOINT, info, method="POST")
        # self.logger.info(str(content))
        return success, content

    def workbooks(self, key=None):
        endpoint = WORKBOOKS_ENDPOINT
        if key:
            endpoint = f"{endpoint}{key}"
        success, content = self.rest(endpoint, {}, method="GET")
        # self.logger.info(str(content))
        return success, content

    def get_fips_mode(self):
        try:
            success, info = self.get(SERVER_INFO_ENDPOINT)
            self.fips_mode = info.get("entry", [{}])[0].get("content", {}).get("fips_mode", False)
            return self.fips_mode
        except Exception as e:
            self.logger.info(f"Error in retrieving FIPS mode: {e!s}")
            return False

    def get_hostname(self):
        if self.hostname:
            return self.hostname
        success, info = self.get(SERVER_INFO_ENDPOINT)
        hostname = info.get("entry", [{}])[0].get("content", {}).get("host")
        success, settings = self.get(SERVER_SETTINGS_ENDPOINT)
        ssl = settings.get("entry", [{}])[0].get("content", {}).get("enableSplunkWebSSL")
        port = settings.get("entry", [{}])[0].get("content", {}).get("httpport")
        if hostname and ssl is not None:
            if port and port not in (80, 443):
                port = f":{port}"
            else:
                port = ""
            self.hostname = "http{}://{}{}".format("s" if ssl else "", hostname, port)

        return self.hostname

    def get_return_url(self, search, result):
        hostname = self.get_hostname()
        tm = result.get("_time")
        try:
            tm = int(tm)
        except:
            tm = str(int(time.time()))
        if hostname:
            if search.get("_model"):
                qs = {
                    "q": "| datamodel {} {} search | fields + *".format(
                        search.get("_model"), search.get("_search")
                    ),
                    "latest": tm,
                }
                return "_originating_data_model", f"{hostname}/app/search/search?{urlencode(qs)}"
            elif search.get("_savedsearch"):
                qs = {
                    "q": '| savedsearch "{}"'.format(search.get("_savedsearch")),
                    "latest": tm,
                }
                return "_originating_search", f"{hostname}/app/search/search?{urlencode(qs)}"
        return None, None
