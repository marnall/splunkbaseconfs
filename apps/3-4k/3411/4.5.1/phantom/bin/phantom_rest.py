# File: phantom_rest.py
# Copyright (c) 2016-2025 Splunk Inc.
#
# SPLUNK CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Splunk Inc. is PROHIBITED.

import hashlib
import json
import os
import re
import sys
from copy import deepcopy
from traceback import format_exc
from urllib.parse import unquote, quote, urlparse
from uuid import uuid4

# REST handlers need sys.path setup before importing ta_addonphantom_declare
_SPLUNK_BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
if _SPLUNK_BIN_DIR not in sys.path:
    sys.path.insert(0, _SPLUNK_BIN_DIR)

import splunk
from splunk.rest import BaseRestHandler
from splunk.persistconn.application import PersistentServerConnectionApplication

import ta_addonphantom_declare  # noqa: F401

from requests.exceptions import SSLError

from phantom_config import (
    PhantomConfig,
    PHANTOM_KEY,
    PHANTOM_AR_KEY,
    SEVERITIES,
    SEVERITIES_AR,
    PLAYBOOKS,
    PLAYBOOKS_AR,
    LOGGING_CONFIG,
    ACCEPTED,
    get_safe,
    VERIFY_KEY,
    FIELD_MAPPING,
    ARTIFACT_AR,
    WORKBOOK_KEY,
    WORKBOOK_LAST_SYNC_TIME,
    WORKBOOK_SYNC_KEY,
)
from phantom_instance import PhantomInstance, DEFAULT_CEF_METADATA, DEFAULT_CONTAINS
from phantom_splunk import SERVER_INFO_ENDPOINT, PasswordStoreException
from phantom_imports import DEFAULT_SEVERITIES

COMPONENT = "configuration"
COMPONENT_AR = "ar_relay"
FORWARD_SCRIPT = "phantom_forward.py"
SCHEDULED_TYPE = "scheduled"

SERVER_PERMISSIONS_ERROR = 'On Splunk: Not all required capabilities are are granted to the current user. "phantom_read", "phantom_write", "list_settings", "list_storage_passwords", "rtsearch", "schedule_rtsearch", and "schedule_search" are needed. These capabilities are included in the "phantom" role.'
SERVER_MISSING = "server is missing"


class FieldMapping(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def pretty_form_data(self, form):
        try:
            form_list = dict()
            for key, value in form.items():
                if value == "":
                    return json.loads(key)
                form_list.append({str(key): str(value)})
            return [form_list]
        except:
            return [form]

    def handle_POST(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        form = self.pretty_form_data(self.request["form"])

        post_data = dict()
        delete_item_id = None
        for item in form:
            # If you want to delete, you would do -d action=delete -d id=48801d94-3b68-477b-98e9-3e880903e448
            if item.get("action") and item.get("action").lower() == "delete":
                delete_item_id = item.get("id")
                if not delete_item_id:
                    raise Exception("Field mapping ID is required for DELETE")
                break
            else:
                try:
                    mapping = {"cim": item["cim"], "cef": item["cef"]}
                    if item.get("contains") is not None:
                        mapping["contains"] = item["contains"]
                    if item.get("id") is not None:
                        mapping["id"] = item.get("id")
                        post_data.update({item.get("id"): mapping})
                    else:
                        uuid = str(uuid4())
                        mapping["id"] = uuid
                        post_data.update({uuid: mapping})
                except Exception:
                    config.logger.error(f"Error posting {item}")

        current_mappings = config.get(FIELD_MAPPING, {})
        updated_mappings = current_mappings

        cim_map = dict()
        for i in current_mappings:
            cim_map[current_mappings[i]["cim"]] = i

        if delete_item_id is None:
            updated_mappings.update(post_data)
        else:
            if isinstance(delete_item_id, str):
                delete_item_id = [delete_item_id]
            if isinstance(delete_item_id, list):
                for i in delete_item_id:
                    try:
                        config.logger.debug(f"DELETE field_mapping - ID: {i}")
                        del updated_mappings[i]
                    except Exception as e:
                        config.logger.error(f"Error deleting {i} {e}")

        # Save the update
        try:
            config[FIELD_MAPPING] = updated_mappings
        except splunk.AuthorizationFailed:
            raise Exception(SERVER_PERMISSIONS_ERROR)
        return {"success": True, "status": 200, "mappings": updated_mappings}

    def handle_GET(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            config.logger.info("Retrieving field mappings...")
            mappings = get_safe(config, FIELD_MAPPING, {})
            formatted_mappings = []
            for key, value in mappings.items():
                updated_value = value
                updated_value.update({"id": key})
                formatted_mappings.append(updated_value)
            # config.logger.info(dict([(x, '') for x in mappings]))
            # return {
            #     "formatted_mappings": formatted_mappings,
            #     "mappings": mappings
            # }
            return mappings
            # return dict([(x, '') for x in mappings])
        except Exception as e:
            msg = format_exc()
            config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


class UpdatePhantomARConfig(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def handle_POST(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)

        logging_key = get_safe(config, LOGGING_CONFIG, "DEBUG")
        config.update_log_level(logging_key)

        current_configs = get_safe(config, PHANTOM_AR_KEY, {})
        form = json.loads(json.dumps(self.request["form"]))
        try:
            action = json.loads(list(form)[0]).get("action")
            config_to_delete = json.loads(list(form)[0]).get("config")
        except:
            action = json.loads(form.keys()[0]).get("action")
            config_to_delete = json.loads(form.keys()[0]).get("config")
        guid = config_to_delete.get("guid")
        if action == "delete":
            try:
                guid_list = current_configs.get(guid)
                updated_list = [
                    x
                    for x in guid_list
                    if x.get("ph_auth_config_id") != config_to_delete.get("ph_auth_config_id")
                ]
                current_configs[guid] = updated_list
                if current_configs[guid] == []:
                    del current_configs[guid]
            except Exception as e:
                config.logger.debug(f"Error: {e}")

        config.logger.debug(f"Updated list of AR configs to save: {current_configs}")

        # Save the update
        try:
            config[PHANTOM_AR_KEY] = current_configs
        except splunk.AuthorizationFailed:
            raise Exception(SERVER_PERMISSIONS_ERROR)
        return {"success": True, "status": 200}


class UpdatePhantomConfig(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def handle_POST(self):
        saved_config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            form = json.loads(json.dumps(self.request["form"]))
            try:
                server_configs = json.loads(self.request["form"]["config"])
                do_save = json.loads(self.request["form"]["save"])
            except:
                server_configs = json.loads(list(form)[0]).get("config")
                do_save = json.loads(list(form)[0]).get("save")

            if do_save is True:
                saved_config.logger.info("Updating SOAR server configurations...")
            else:
                saved_config.logger.info("Running Test Connectivity...")

            new_server_configs = {}
            servers = []
            for cur_config in server_configs:
                tmp_cur_config = cur_config
                saved_config.logger.debug("Checking '{}'".format(tmp_cur_config.get("custom_name")))
                if not tmp_cur_config.get("arrelay"):
                    tmp_cur_config["arrelay"] = False
                response = response_json = None
                if do_save is True and not tmp_cur_config.get("server_validated"):
                    raise Exception(
                        "Server URL is not validated. Acknowledge that you understand your credentials will be used to securely connect to the Splunk SOAR server address you entered. You must verify this address is accurate and points to the intended destination."
                    )
                if not tmp_cur_config.get("server", "").lower().startswith("https://"):
                    raise Exception("SOAR only supports https, please update your server config.")
                # Strip anything outside of https://<host>:<port>
                try:
                    url = urlparse(tmp_cur_config.get("server"))
                    result = (
                        url.scheme == "https"
                        and url.path == ""
                        and url.params == ""
                        and url.query == ""
                        and url.fragment == ""
                        and url.netloc
                    )
                    if (
                        result is False
                        or (url.port and not isinstance(url.port, int) and url.port >= 65535)
                        or tmp_cur_config.get("server", "")[-1] in ["?", "#", ":", "."]
                    ):
                        raise Exception(
                            "Invalid server URL. Please check the server URL and try again."
                        )
                except Exception:
                    saved_config.logger.error(format_exc())
                    raise Exception(
                        "Failed to parse server URL. Please check the server URL and try again."
                    )
                try:
                    if not tmp_cur_config.get("ph-auth-token"):
                        raise PasswordStoreException(
                            "Failed to load auth token from credential store. User needs permission to access storage/passwords."
                        )
                    tmp_cur_config["ph-auth-token"] = unquote(tmp_cur_config.get("ph-auth-token"))
                    pi = PhantomInstance(
                        tmp_cur_config,
                        saved_config.logger,
                        verify=saved_config[VERIFY_KEY],
                        fips_enabled=saved_config.fips_is_enabled,
                    )
                    if tmp_cur_config.get("validate") is True:
                        _, _ = pi.verify_server()
                    else:
                        new_server_configs[tmp_cur_config.get("ph_auth_config_id")] = tmp_cur_config
                    if do_save is True:
                        servers.append(tmp_cur_config.get("ph_auth_config_id"))
                        new_server_configs[pi.ph_auth_config_id] = pi.json()
                        # save the updated password
                        saved_config.update_password(
                            tmp_cur_config.get("ph_auth_config_id"),
                            tmp_cur_config.get("ph-auth-token"),
                        )
                    # AR Relay: create list of servers that should be on SH forwarding to HF
                    # if cur_config.get('arrelay') is True:
                    #     temp_config = cur_config
                    #     del temp_config['ph-auth-token']
                    #     ar_relay_configs[cur_config.get('ph_auth_config_id')] = temp_config
                except PasswordStoreException as e:
                    return {
                        "error": {
                            "custom_name": json.dumps(tmp_cur_config.get("custom_name")),
                            "message": f"{e!s}",
                        },
                        "status": 400,
                    }
                except splunk.AuthorizationFailed:
                    raise Exception(
                        "Insufficient permissions to store password. Consult your Splunk administrator"
                    )
                except SSLError:
                    message = 'Could not communicate with user "{}" on SOAR server "{}".'.format(
                        tmp_cur_config["user"], tmp_cur_config["server"]
                    )
                    if do_save is True:
                        raise Exception(message)
                except Exception:
                    saved_config.logger.error(format_exc())
                    # saved_config.logger.info(os.environ)
                    message = 'Failed to communicate with user "{}" on SOAR server "{}".'
                    message = message.format(tmp_cur_config["user"], tmp_cur_config["server"])
                    if do_save is True:
                        raise Exception(message)
                    else:
                        return {
                            "error": {
                                "custom_name": json.dumps(tmp_cur_config.get("custom_name")),
                                "message": f"{message}",
                            },
                            "status": 400,
                        }
            if do_save is True:
                saved_config.logger.info("Saving configurations...")
                try:
                    saved_config[PHANTOM_KEY] = new_server_configs
                    saved_config[ACCEPTED] = (
                        self.request["form"].get(ACCEPTED) == "true" and True
                    ) or False
                except splunk.AuthorizationFailed:
                    raise Exception(SERVER_PERMISSIONS_ERROR)
                try:
                    # update the password store here, even if it means to delete
                    saved_config.logger.info("Updating passwords...")
                    current_passwords_list = saved_config.get_passwords()
                    remaining_wanted = []
                    for tmp_cur_config in server_configs:
                        i = tmp_cur_config.get("ph_auth_config_id")
                        try:
                            name = hashlib.sha1(i.encode()).hexdigest()
                        except:
                            name = hashlib.sha1(i).hexdigest()
                        remaining_wanted.append(name)
                    for i in current_passwords_list:
                        if i not in remaining_wanted:
                            saved_config.delete_password(i)
                except:
                    pass
                try:
                    saved_config.logger.info("Cleaning severities...")
                    current_severities = saved_config[SEVERITIES]
                    new_server_severities = {
                        key: value for key, value in current_severities.items() if key in servers
                    }
                    saved_config[SEVERITIES] = new_server_severities
                except:
                    pass
                try:
                    saved_config.logger.info("Cleaning playbooks...")
                    current_playbooks = saved_config[PLAYBOOKS]
                    new_server_playbooks = {
                        key: value for key, value in current_playbooks.items() if key in servers
                    }
                    saved_config[PLAYBOOKS] = new_server_playbooks
                except:
                    pass
                # AR Relay: post the configs to KVStore
                # try:
                #     saved_config.logger.debug("going to post to collection now")
                #     success, content = saved_config.splunk.post_kvstore(kv_collection='phantom_conf', method='POST', data=ar_relay_configs)
                # except Exception as e:
                #     saved_config.logger.debug("Error posting collection data: {}".format(e))
            return {
                "success": True,
                "status": 200,
            }
        except Exception as e:
            msg = format_exc()
            saved_config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


class TargetPlaybookAR(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def handle_GET(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            config.logger.info("Retrieving playbooks and playbooks AR...")
            # Map the config IDs to their playbooks and append the names in the form "custom_name: playbook"
            formatted_playbooks = []
            defaults = []
            targets = get_safe(config, PHANTOM_KEY, {})
            playbooks = get_safe(config, PLAYBOOKS, {})
            for t in targets:
                p = playbooks.get(t, None)
                if p:
                    if targets[t]["default"] in [True, "Default"]:
                        defaults = [f"Default: {x}" for x in playbooks.get(t)]
                    tmp = ["{}: {}".format(targets[t]["custom_name"], x) for x in playbooks.get(t)]
                    formatted_playbooks += tmp

            targetsAR = get_safe(config, PHANTOM_AR_KEY, {})
            playbooksAR = get_safe(config, PLAYBOOKS_AR, {})
            for server in targetsAR:
                server_configs = targetsAR[server]
                for t in server_configs:
                    server_playbooks = playbooksAR.get(server, {})
                    config_id = t.get("ph_auth_config_id")
                    if config_id:
                        p = server_playbooks.get(config_id)
                        if p:
                            tmp = [
                                "{} (ARR): {}".format(t.get("custom_name"), x)
                                for x in server_playbooks.get(config_id)
                            ]
                            formatted_playbooks += tmp
            formatted_playbooks = sorted(formatted_playbooks)
            if defaults:
                formatted_playbooks = defaults + formatted_playbooks

            return dict([(x, "") for x in formatted_playbooks])
        except Exception as e:
            msg = format_exc()
            config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


class TargetPlaybook(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    # Update or append to the current [playbooks]
    def updatePlaybooks(self, config, incoming_playbooks, live_servers):
        current_playbooks = config.get(PLAYBOOKS, "")  # dict
        if current_playbooks == "":
            return incoming_playbooks
        # Want to remove the stale playbooks that don't even have their server attached to this instance anymore
        current_playbook_servers = list(current_playbooks.keys())
        updated_playbooks = current_playbooks

        for item in current_playbook_servers:
            if item not in live_servers:
                del updated_playbooks[item]
        for _ in incoming_playbooks:
            additional_playbook = {
                playbook: incoming_playbooks[playbook]
                for playbook in incoming_playbooks.keys()
                if playbook in incoming_playbooks
            }
            updated_playbooks.update(additional_playbook)
        return updated_playbooks

    # Get playbooks for associated config
    def handle_POST(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            live_servers = get_safe(config, PHANTOM_KEY, {})
            config.logger.info("Posting playbooks...")
            server_configs = json.loads(list(self.request["form"])[0]).get("config", {})
            try:
                live_servers = list(live_servers.keys())
            except splunk.AuthorizationFailed:
                raise Exception(SERVER_PERMISSIONS_ERROR)
            playbooks = {}
            for cur_config in server_configs:
                config.logger.debug(
                    "Attempting to retrieve playbooks for '{}'...".format(
                        cur_config.get("custom_name")
                    )
                )
                response = response_json = None
                if not cur_config.get("server", "").lower().startswith("https://"):
                    config.logger.error(cur_config.get("server", SERVER_MISSING))
                    raise Exception("SOAR only supports https, please update your server config.")
                try:
                    if not cur_config.get("ph-auth-token"):
                        raise PasswordStoreException(
                            "Failed to load auth token from credential store. User needs permission to access storage/passwords."
                        )
                    if not cur_config.get("arrelay"):
                        cur_config["arrelay"] = False
                    if not cur_config.get("relay"):
                        cur_config["relay"] = None
                    cur_config["ph-auth-token"] = unquote(cur_config.get("ph-auth-token"))
                    pi = PhantomInstance(
                        cur_config,
                        config.logger,
                        verify=config[VERIFY_KEY],
                        fips_enabled=config.fips_is_enabled,
                    )
                    playbooks[pi.ph_auth_config_id], err = pi.get_playbooks()
                    if err is not None:
                        return {
                            "error": {
                                "custom_name": json.dumps(cur_config.get("custom_name")),
                                "message": err,
                            },
                            "status": 400,
                        }
                except Exception as e:
                    return {
                        "error": {
                            "custom_name": json.dumps(cur_config.get("custom_name")),
                            "message": "Error retrieving playbooks for {}. {}".format(
                                cur_config.get("custom_name"), str(e)
                            ),
                        },
                        "status": 400,
                    }

            updated_playbooks = self.updatePlaybooks(config, playbooks, live_servers)
            try:
                config[PLAYBOOKS] = updated_playbooks
                config[ACCEPTED] = (self.request["form"].get(ACCEPTED) == "true" and True) or False
                config.logger.debug("Playbooks updated")
            except splunk.AuthorizationFailed:
                raise Exception(SERVER_PERMISSIONS_ERROR)
            return {"success": True, "status": 200}
        except Exception as e:
            msg = format_exc()
            config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }

    def handle_GET(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            config.logger.info("Retrieving playbooks...")
            # Map the config IDs to their playbooks and append the names in the form "custom_name: playbook"
            formatted_playbooks = []
            defaults = []
            targets = get_safe(config, PHANTOM_KEY, {})
            playbooks = get_safe(config, PLAYBOOKS, {})
            for t in targets:
                p = playbooks.get(t, None)
                if p:
                    if targets[t]["default"] == True:
                        defaults = [f"Default: {x}" for x in playbooks.get(t)]
                    tmp = ["{}: {}".format(targets[t]["custom_name"], x) for x in playbooks.get(t)]
                    formatted_playbooks += tmp

            formatted_playbooks = sorted(formatted_playbooks)

            if defaults:
                formatted_playbooks = defaults + formatted_playbooks

            return {
                "results": dict(
                    (x, formatted_playbooks[x]) for x in range(len(formatted_playbooks))
                ),
                "status": 200,
            }
        except Exception as e:
            msg = format_exc()
            config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


class CefMetadata(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def handle_GET(self):
        saved_config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            saved_config.logger.info("Retrieving cef metadata...")
            # target = self.request['query'].get('target')
            # target_obj = saved_config[PHANTOM_KEY].get(target)
            # if not target_obj:
            #    raise Exception('Missing required field "target"')
            # pi = PhantomInstance(target_obj, saved_config.logger)
            return {
                "cef_metadata": DEFAULT_CEF_METADATA,
                "all_contains": DEFAULT_CONTAINS,
                "cim_fields": saved_config.get_cim_mapping(),
                "status": 200,
            }
        except Exception as e:
            msg = format_exc()
            saved_config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


class TargetList(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def handle_GET(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            config.logger.info("Retrieving list of SOAR server configurations...")
            targets = get_safe(config, PHANTOM_KEY, {})
            ltr = []
            has_default = False
            for i in targets:
                if targets[i]["default"]:
                    has_default = True
                ltr.append(targets[i]["custom_name"])

            ltr = sorted(ltr)

            if has_default:
                ltr.insert(0, "Default")
            config.logger.info(dict([(x, "") for x in ltr]))
            return dict([(x, "") for x in ltr])
        except Exception as e:
            msg = format_exc()
            config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


class TargetListAR(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def handle_GET(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            config.logger.info("Retrieving list of SOAR server configurations...")
            targetsLocal = get_safe(config, PHANTOM_KEY, {})
            targetsHF = get_safe(config, PHANTOM_AR_KEY, {})
            ltr = []
            has_default = False
            for i in targetsLocal:
                if targetsLocal[i]["default"]:
                    has_default = True
                ltr.append(targetsLocal[i]["custom_name"])
            for i in targetsHF:
                for server in targetsHF[i]:
                    ltr.append("{} (ARR)".format(server.get("custom_name")))

            ltr = sorted(ltr)

            if has_default:
                ltr.insert(0, "Default")
            config.logger.info(dict([(x, "") for x in ltr]))
            return dict([(x, "") for x in ltr])
        except Exception as e:
            msg = format_exc()
            config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


class TargetSeverityAR(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def handle_GET(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            config.logger.info("Retrieving severities and severities AR...")
            # Map the config IDs to their severities and append the names in the form "custom_name: playbook"
            formatted_severities = []
            defaults = []
            targets = get_safe(config, PHANTOM_KEY, {})
            severities = get_safe(config, SEVERITIES, {})
            for t in targets:
                s = severities.get(t)
                if not s:
                    s = list(DEFAULT_SEVERITIES.values())
                if targets[t]["default"] in [True, "Default"]:
                    defaults = [f"Default: {x}" for x in s]
                tmp = ["{}: {}".format(targets[t]["custom_name"], x) for x in s]
                formatted_severities += tmp
            targetsAR = get_safe(config, PHANTOM_AR_KEY, {})
            severitiesAR = get_safe(config, SEVERITIES_AR, {})
            for server in targetsAR:
                server_configs = targetsAR[server]
                for t in server_configs:
                    server_severities = severitiesAR.get(server, {})
                    config_id = t.get("ph_auth_config_id", "")
                    s = server_severities.get(config_id)
                    if not s:
                        s = list(DEFAULT_SEVERITIES.values())
                    tmp = ["{} (ARR): {}".format(t.get("custom_name"), x) for x in s]
                    formatted_severities += tmp
            formatted_severities = sorted(formatted_severities)
            if defaults:
                formatted_severities = defaults + formatted_severities
            return dict([(x, "") for x in formatted_severities])
        except Exception as e:
            msg = format_exc()
            config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


class TargetSeverity(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    # Update or append to the current [severities]
    def updateSeverities(self, config, incoming_severities, live_servers):
        current_severities = config.get(SEVERITIES, None)  # dict
        if current_severities is None:
            return incoming_severities

        # Want to remove the stale severity that don't even have their server attached to this instance anymore
        current_severity_servers = list(current_severities.keys())
        updated_severities = current_severities
        for item in current_severity_servers:
            if item not in live_servers:
                del updated_severities[item]
        for server in incoming_severities:
            updated_severities.update({server: incoming_severities[server]})
        return updated_severities

    def handle_POST(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            live_servers = get_safe(config, PHANTOM_KEY, {})
            config.logger.info("Posting severities...")
            server_configs = json.loads(list(self.request["form"])[0]).get("config", {})
            try:
                live_servers = list(live_servers.keys())
            except splunk.AuthorizationFailed:
                raise Exception(SERVER_PERMISSIONS_ERROR)
            severities = {}
            errors = []
            for cur_config in server_configs:
                config.logger.debug(
                    "Attempting to retrieve severities for '{}'...".format(
                        cur_config.get("custom_name")
                    )
                )
                if not cur_config.get("server", "").lower().startswith("https://"):
                    config.logger.error(cur_config.get("server", SERVER_MISSING))
                    raise Exception("SOAR only supports https, please update your server config.")
                try:
                    if not cur_config.get("ph-auth-token"):
                        raise PasswordStoreException(
                            "Failed to load auth token from credential store. User needs permission to access storage/passwords."
                        )
                    if not cur_config.get("arrelay"):
                        cur_config["arrelay"] = False
                    if not cur_config.get("relay"):
                        cur_config["relay"] = None
                    cur_config["ph-auth-token"] = unquote(cur_config.get("ph-auth-token"))
                    pi = PhantomInstance(
                        cur_config,
                        config.logger,
                        verify=config[VERIFY_KEY],
                        fips_enabled=config.fips_is_enabled,
                    )
                    severities[pi.ph_auth_config_id], err = pi.get_severities()
                    if err is not None:
                        errors.append(
                            {
                                "custom_name": json.dumps(cur_config.get("custom_name")),
                                "message": err,
                            }
                        )
                except Exception as e:
                    config.logger.error(e)
                    return {
                        "error": {
                            "custom_name": json.dumps(cur_config.get("custom_name")),
                            "message": "Error retrieving severities for {}. {}".format(
                                cur_config.get("custom_name"), str(e)
                            ),
                        },
                        "status": 400,
                    }

            updated_severities = self.updateSeverities(config, severities, live_servers)
            try:
                config[SEVERITIES] = updated_severities
                config[ACCEPTED] = (self.request["form"].get(ACCEPTED) == "true" and True) or False
            except splunk.AuthorizationFailed:
                raise Exception(SERVER_PERMISSIONS_ERROR)
            status = 200 if len(errors) == 0 else 400
            success = True if len(errors) == 0 else False
            return {"success": success, "status": status, "error": errors}
        except Exception as e:
            msg = format_exc()
            config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }

    def handle_GET(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            config.logger.info("Retrieving severities...")
            formatted_severities = []
            defaults = []
            targets = get_safe(config, PHANTOM_KEY, {})
            severities = get_safe(config, SEVERITIES, {})
            for t in targets:
                s = severities.get(t)
                if s:
                    if targets[t]["default"] == True:
                        defaults = [f"Default: {x}" for x in severities.get(t)]
                    tmp = ["{}: {}".format(targets[t]["custom_name"], x) for x in severities.get(t)]
                    formatted_severities += tmp
                else:
                    if targets[t]["default"] == True:
                        defaults = [f"Default: {v}" for k, v in DEFAULT_SEVERITIES.items()]
                    tmp = [
                        "{}: {}".format(targets[t]["custom_name"], v)
                        for k, v in DEFAULT_SEVERITIES.items()
                    ]
                    formatted_severities += tmp

            formatted_severities = sorted(formatted_severities)

            if defaults:
                formatted_severities = defaults + formatted_severities

            return dict([(x, "") for x in formatted_severities])
        except Exception as e:
            msg = format_exc()
            config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


class UpsertDataForwarding(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def dup_savedsearch(self, config, search_request):
        search_name = search_request.get("_savedsearch")
        content = config.splunk.get_savedsearch(search_name)
        entries = content.get("entry", [])
        if not entries:
            raise Exception("Failed to load saved search (no entries)")
        query = search_request["_query"] = '| savedsearch "{}"'.format(
            search_name.replace('"', '\\"')
        )
        search_request["_preview"] = '| savedsearch "{}"'.format(search_name.replace('"', '\\"'))

        if not search_request.get("_earliest_time"):
            search_request["_earliest_time"] = "-{}m".format(int(search_request["_minutes"]) * 2)
            search_request["_latest_time"] = ""

        rest_qs_fields = {
            "name": lambda d: "_phantom_app_" + d["_name"],
            "search": lambda d: d["_query"],
            "action.script": lambda d: 1,
            "actions": lambda d: "phantomeventforwarding",
            # 'action.script.filename': lambda d: FORWARD_SCRIPT,
            "action.phantomeventforwarding": lambda d: 1,
            "action.phantomeventforwarding.param.config_id": lambda d: d["_id"],
            "dispatch.earliest_time": lambda d: (
                "rt"
                if search_request["_schedule"] == "realtime" and "rt"
                else "{}".format(unquote(search_request["_earliest_time"]))
            ),
            "dispatch.index_earliest": lambda d: (
                "rt" if search_request["_schedule"] == "realtime" and "rt" else ""
            ),
            "dispatch.index_latest": lambda d: (
                "rt" if d["_schedule"] == "realtime" and "rt" else ""
            ),
            "dispatch.latest_time": lambda d: (
                "rt"
                if search_request["_schedule"] == "realtime" and "rt"
                else "{}".format(unquote(d["_latest_time"]))
            ),
            "is_scheduled": lambda d: 1,
            "cron_schedule": self._cron_format,
            "output_mode": lambda d: "json",
            "disabled": lambda d: (d["_enabled"] != True and 1) or 0,
            "alert.digest_mode": lambda d: 1,
            "alert_comparator": lambda d: "greater than",
            "alert_threshold": lambda d: 0,
        }
        if search_request["_schedule"] == "scheduled":
            rest_qs_fields.update({"alert_type": lambda d: "number of events"})
        return rest_qs_fields

    def _cron_format(self, search_dict):
        if search_dict["_schedule"] == SCHEDULED_TYPE:
            try:
                hours = "*"
                minutes = int(search_dict["_minutes"])
                if minutes <= 0 or minutes >= (60 * 24):
                    raise Exception
                if minutes >= 60:
                    min_to_hour = minutes // 60
                    hours = "*/" + str(min_to_hour)
                    minutes = minutes % 60
                else:
                    minutes = "*/" + str(minutes)
            except Exception:
                raise Exception('Missing or malformed "minutes"')
            cron_format = f"{minutes} {hours} * * *"
            return cron_format
        else:
            return "* * * * *"

    def handle_POST(self):
        orig_name = None
        new_name = None
        orig_search = None
        _id = None
        config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            search = None
            try:
                search = json.loads(self.request["form"]["data"])
            except Exception:
                search = json.loads(list(self.request["form"])[0]).get("data", {})
            config.logger.info(f"search: {search}")
            _id = search.get("_id")
            if not _id:
                _id = str(uuid4())
            orig_search = config.get(_id, {})
            orig_name = orig_search.get("_name")
            if "_" in search:
                del search["_"]
            search["_name"] = new_name = search.get("_name").strip()
            search["_id"] = _id
            all_configs = config.get_forwarding_configs()
            for cfg in all_configs:
                if cfg["_name"] == new_name and cfg["_id"] != _id:
                    raise Exception(
                        f'Forwarding configuration with name "{unquote(new_name)}" already exists.'
                    )
            is_savedsearch = False
            if search["_name"].startswith("_phantom_app_"):
                raise Exception(
                    "Cannot use a _phantom_app saved search in a forwarding configuration"
                )
            if search.get("_savedsearch"):
                rest_qs_fields = self.dup_savedsearch(config, search)
                is_savedsearch = True
            else:
                rest_qs_fields = {
                    "name": lambda d: "_phantom_app_" + d["_name"],
                    "search": lambda d: "| datamodel {_model} {_search} search | fields + *".format(
                        **d
                    ),
                    "action.script": lambda d: 1,
                    "actions": lambda d: "phantomeventforwarding",
                    # 'action.script.filename': lambda d: FORWARD_SCRIPT,
                    "action.phantomeventforwarding": lambda d: 1,
                    "action.phantomeventforwarding.param.config_id": lambda d: d["_id"],
                    "is_scheduled": lambda d: 1,
                    "cron_schedule": self._cron_format,
                    "output_mode": lambda d: "json",
                    "disabled": lambda d: (d["_enabled"] != True and 1) or 0,
                    "alert.digest_mode": lambda d: 1,
                    "alert_comparator": lambda d: "greater than",
                    "alert_threshold": lambda d: 0,
                }
                if search["_schedule"] == "scheduled":
                    rest_qs_fields.update({"alert_type": lambda d: "number of events"})
                if search.get("_dispatch") == "indextime":
                    rest_qs_fields.update(
                        {
                            "dispatch.earliest_time": lambda d: (
                                "rt"
                                if d["_schedule"] == "realtime" and "rt"
                                else "-{}m".format(2 * int(d["_minutes"]))
                            ),
                            "dispatch.index_earliest": lambda d: (
                                (d["_schedule"] == "realtime" and "rt")
                                or "-{}m".format(d["_minutes"])
                            ),
                            "dispatch.index_latest": lambda d: (
                                (d["_schedule"] == "realtime" and "rt") or ""
                            ),
                            "dispatch.latest_time": lambda d: (
                                "rt" if d["_schedule"] == "realtime" and "rt" else ""
                            ),
                        }
                    )
                else:  # dispatch _time
                    rest_qs_fields.update(
                        {
                            "dispatch.earliest_time": lambda d: (
                                (d["_schedule"] == "realtime" and "rt")
                                or "-{}m".format(d["_minutes"])
                            ),
                            "dispatch.latest_time": lambda d: (
                                (d["_schedule"] == "realtime" and "rt") or ""
                            ),
                        }
                    )

                search["_preview"] = rest_qs_fields["search"](search)
            qs = {}
            for k, v in rest_qs_fields.items():
                v = v(search)
                if v is not None:
                    qs[k] = v
            new_name = qs["name"]
            if not search.get("_savedsearch"):
                search["_query"] = qs["search"]
            for k in list(search.keys()):
                v = search.pop(k)
                k = k.strip()
                if k.endswith("[]") and isinstance(v, str):
                    v = v.split(",")
                search[k] = v
            if is_savedsearch:
                searches = config.splunk.get_saved_searches(search["_savedsearch"])
                if search["_savedsearch"] not in searches:
                    raise Exception('Saved search "{}" not found'.format(search["_savedsearch"]))
            else:
                models = config.splunk.get_data_models()
                if search["_model"] not in models:
                    raise Exception('Data model "{}" not found'.format(search["_model"]))
                search["_prefixes"] = models[search["_model"]][search["_search"]]["prefixes"]

            search["_send_method"] = "custom_alert_action"
            config[_id] = search
            success = False

            # Check if this is a new or existing saved search
            searches = config.splunk.get_savedsearch(qs["name"])
            new_search = False if searches else True
            if search.get("_migration") == True:
                new_search = True

            try:
                if orig_name:
                    orig_name = "_phantom_app_" + orig_name
                    if orig_name != new_name:
                        config.splunk.delete_saved_search(orig_name)
                config.splunk.delete_saved_search(new_name)
            except Exception:
                config.logger.error(format_exc())
            success, content = config.splunk.save_savedsearch(qs, new_search)

            if not success:
                raise Exception(content)

        except Exception as e:
            msg = format_exc() + "\n" + str(self.request["form"])
            config.logger.error(msg)
            try:
                if not orig_name:
                    del config[_id]
                elif not orig_name != new_name:
                    config[_id] = orig_search
            except Exception:
                config.logger.error(f'Failed to restore config "{_id}"')
            return {
                "error": str(e),
                "status": 400,
            }
        return {
            "success": True,
            "status": 200,
            "_id": _id,
        }


class PreviewSearch(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def handle_GET(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            success = False
            _id = self.request["query"].get("id")
            search = config.get(_id)
            if not search:
                raise Exception("Search ID not found")
            args = {
                "search": search["_preview"] + " | head 5",
            }
            window = self.request["query"].get("preview_window", "all")
            if window in ("5m", "1h", "1d"):
                dispatch = (
                    "index_earliest" if search.get("_dispatch") == "indextime" else "earliest_time"
                )
                args[dispatch] = "-" + window
            success, content = config.splunk.search(args)
            if not success:
                raise Exception(content)
            response = {"success": True}
            response["results"] = results = []
            for j_str in content.splitlines():
                j = json.loads(j_str)
                res = j.get("result", {})
                if not res:
                    continue
                cef = PhantomInstance.find_patterns(res, search)
                result = {
                    "_raw": res.get("_raw", ""),
                    "_meta": search,
                    "_raw_plus": res,
                    "_cef": cef,
                }
                result.update(cef)
                results.append(result)
            return response
        except Exception as e:
            msg = format_exc()
            config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


class SearchForRelays(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def literal_eval(self, s):
        new_string = s.replace('"', '\\"').replace("u'", "'")
        new_string = (
            new_string.replace("'", '"').replace(" True", " true").replace(" False", " false")
        )
        new_string = json.loads(new_string)
        return new_string

    def handle_GET(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        # set log level based on phantom.conf enable_logging
        logging_key = get_safe(config, LOGGING_CONFIG, "DEBUG")
        config.update_log_level(logging_key)
        config.logger.info("Searching for configurations, playbooks, and severities...")
        # head 3 because it could be either config, playbook, or severity as latest result
        search = 'search index=main source=*/var/log/splunk/phantom_ar_relay.log source!="*/var/log/splunk/python.log" source!="*/var/log/splunk/phantom_configuration.log" | search NOT __init__: | search NOT phantom_config | head 150 | sort -_time asc'
        _, content = config.splunk.search({"search": search, "eventSorting": "asc"})
        try:
            content = content.decode()
        except (UnicodeDecodeError, AttributeError):
            pass
        content = content.replace("\\", "")

        phantom_ar = get_safe(config, PHANTOM_AR_KEY, {})
        playbook_ar = get_safe(config, PLAYBOOKS_AR, {})
        severities_ar = get_safe(config, SEVERITIES_AR, {})

        p_conf = re.compile(r":::configs:(.*):::")
        results_conf = p_conf.findall(content)
        results_conf = self.literal_eval(results_conf[0])
        if not results_conf:
            phantom_ar = {}
            playbook_ar = {}
            severities_ar = {}
        for item in results_conf:
            key = item
            value = results_conf[item]
            phantom_ar[key] = value

        if phantom_ar:
            try:
                # playbooks are chunked due to 999 limit
                p_play = re.compile(
                    r":::playbooks:([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}):(\d+):(.*):::"
                )
                results_for_guid = p_play.findall(content)
                results_play = p_play.findall(content)
                guid = results_for_guid[0][0]
            except Exception as e:
                msg = "Could not retrieve playbook chunk identifier"
                config.logger.error(msg)
                config.logger.debug(e)
                raise Exception(msg)

            rebuilding_playbooks = ""
            sorted_resulting_playbooks = [item for item in results_play if item[0] == guid]
            # sometimes the order is already there
            last_num = 00
            orig_in_order = True
            for item in sorted_resulting_playbooks:
                if int(item[1]) + 1 == last_num + 1:
                    last_num += 1
                else:
                    orig_in_order = False
                    break
            if orig_in_order is False:
                sorted_resulting_playbooks = list(
                    dict.fromkeys(sorted(sorted_resulting_playbooks, key=lambda x: x[1]))
                )
            for item in sorted_resulting_playbooks:
                rebuilding_playbooks = rebuilding_playbooks + item[2]
            rebuilding_playbooks = json.loads(rebuilding_playbooks)
            for key, value in rebuilding_playbooks.items():
                unquoted_value = {vk: [unquote(vi) for vi in vv] for vk, vv in value.items()}
                playbook_ar[key] = unquoted_value
            try:
                s_sev = re.compile(r":::severities:(.*):::")
                results_for_guid = s_sev.findall(content)
                severities_ar = json.loads(results_for_guid[0])
            except Exception as e:
                msg = "Could not retrieve severities"
                config.logger.error(msg)
                config.logger.debug(e)
                raise Exception(msg)

        # if the HF is emptied out, the dictionary key will remain, but it will be empty
        if len(phantom_ar) == 0:
            msg = "No config results returned from search"
            config.logger.error(msg)
        if len(playbook_ar) == 0:
            msg = "No playbook results returned from search"
            config.logger.error(msg)
        if len(severities_ar) == 0:
            msg = "No severities results returned from search"
            config.logger.error(msg)
        try:
            config[PHANTOM_AR_KEY] = phantom_ar
            config[PLAYBOOKS_AR] = playbook_ar
            config[SEVERITIES_AR] = severities_ar
        except Exception as e:
            config.logger.debug(f"Error posting phantom_ar data: {e}")
            raise Exception(e)

        return {"success": True, "num_configs": len(phantom_ar), "num_playbooks": len(playbook_ar)}


class PushData(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def handle_POST(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        # set log level based on phantom.conf enable_logging
        logging_key = get_safe(config, LOGGING_CONFIG, "DEBUG")
        config.update_log_level(logging_key)
        try:
            try:
                info = json.loads(self.request["form"]["info"])
            except Exception:
                info = json.loads(list(self.request["form"])[0]).get("info", {})
            response = {}
            info["cef"]["_container_name"] = unquote(info.get("cef", {}).get("_container_name", ""))
            raw = info["raw"]
            cef = info["cef"]
            search = config[info["search"]]
            target = config.get_server_config(info["target"])
            if not target.get("arrelay"):
                target["arrelay"] = False
            pi = PhantomInstance(
                target,
                config.logger,
                verify=config[VERIFY_KEY],
                fips_enabled=config.fips_is_enabled,
            )
            artifacts = pi.create_artifacts(cef, raw, search)
            if artifacts:
                artifact = artifacts[0]
                key, value = config.splunk.get_return_url(search, artifact.get("data", {}))
                if key and value:
                    artifact["cef"][key] = value
                created, container_id, resp = pi.get_or_create_container(artifact, cef, search)
                if container_id is None:
                    config.logger.info(
                        "Could not create container. Check that the severity is valid."
                    )
                    return {
                        "error": "The artifact has not been created. Check that the severity is valid.",
                        "status": 400,
                    }
                else:
                    config.logger.info({"new_container": container_id})
                for artifact in artifacts:
                    artifact["container_id"] = container_id
                    artifact_id = pi.post_artifact(artifact)
                    config.logger.info({"new artifact": artifact_id})
                    container_id = artifact_id[3] if artifact_id[3] is not None else container_id
            response["success"] = True
            response["message"] = "Successfully sent entry to SOAR"
            response["container_id"] = container_id
            response["url"] = target["server"] + "/mission/" + str(container_id)
            return response
        except Exception as e:
            msg = format_exc()
            config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


class ArtifactAR(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def handle_POST(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        # set log level based on phantom.conf enable_logging
        logging_key = get_safe(config, LOGGING_CONFIG, "DEBUG")
        config.update_log_level(logging_key)
        config.logger.info("--- post for AR artifact ---")
        info = None
        try:
            info = json.loads(list(self.request["form"].keys())[0]).get("artifacts")
        except Exception:
            info = self.request["form"].get("artifacts")
        artifacts = "multiple"
        if info == 1 or info == "single":
            artifacts = "single"
        config.logger.info(f"AR artifacts are: {artifacts}")

        # Save the new value
        try:
            config[ARTIFACT_AR] = artifacts
        except splunk.AuthorizationFailed:
            raise Exception(SERVER_PERMISSIONS_ERROR)
        return {"success": True, "status": 200}

    def handle_GET(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        # set log level based on phantom.conf enable_logging
        logging_key = get_safe(config, LOGGING_CONFIG, "DEBUG")
        config.update_log_level(logging_key)
        try:
            value = get_safe(config, ARTIFACT_AR, "")
            config.logger.info(f"Artifact send method: {value}")
            return {"success": True, "value": value}
        except Exception as e:
            msg = format_exc()
            config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


class PushRelayConfigs(BaseRestHandler):
    def __init__(self, *args):
        BaseRestHandler.__init__(self, *args)

    def handle_POST(self):
        config = PhantomConfig(COMPONENT, self.sessionKey)
        # set log level based on phantom.conf enable_logging
        logging_key = get_safe(config, LOGGING_CONFIG, "DEBUG")
        config.update_log_level(logging_key)
        config.logger.info("Creating AR Relay Config event")
        # get safe PHANTOM_KEY
        try:
            phantom_keys = get_safe(config, PHANTOM_KEY, {})
            phantom_playbooks = get_safe(config, PLAYBOOKS, {})
            phantom_severities = get_safe(config, SEVERITIES, {})
        except Exception as e:
            config.logger.error(f"Error: {e}")

        # GUID is the key to distinguish this HF
        try:
            success, content = config.splunk.get(SERVER_INFO_ENDPOINT)
        except Exception as e:
            raise Exception(e)

        if success is True:
            guid = content.get("entry")[0].get("content", {}).get("guid", "")

        # Don't save it to [phantom_ar] because it'll show up in table
        # make it an event, which will be pushed to SH
        ar = PhantomConfig(COMPONENT_AR, self.sessionKey)
        if phantom_keys == {}:
            config[PHANTOM_AR_KEY] = []
            # Empty configs if nothing to push from HF
            ar.logger.info(":::configs:{}:::")
            config.logger.info("Done pushing server configs")

            ar.logger.info(":::playbooks:{}:::")
            config.logger.info("Done pushing playbooks")

            ar.logger.info(":::severities:{}:::")
            config.logger.info("Done pushing severities")
        else:
            # check if server is arrelay=True
            ar_relay_configs = list()
            ar_playbooks = dict()
            ar_severities = dict()
            for cur_config in phantom_keys:
                # if arrelay=True, add it to list
                if phantom_keys[cur_config].get("arrelay") is True:
                    tmp = phantom_keys[cur_config]
                    del tmp["ph-auth-token"]
                    ar_relay_configs.append(tmp)

                    # playbooks
                    playbooks = phantom_playbooks.get(cur_config)
                    if playbooks is not None:
                        ar_playbooks[str(cur_config)] = [quote(x) for x in playbooks]

                    # severities
                    severities = phantom_severities.get(cur_config)
                    if severities is not None:
                        ar_severities[str(cur_config)] = severities

            c = {guid: ar_relay_configs}
            p = json.dumps({guid: ar_playbooks})
            s = json.dumps({guid: ar_severities})

            # set log level based on phantom.conf enable_logging
            ar.update_log_level(logging_key)
            ar.logger.info(f":::configs:{c}:::")
            config.logger.info("Done pushing server configs")
            # playbooks can be a super large list and there is a max byte limit on events.

            random_guid = str(uuid4())  # so you know its part of same chunking
            chunk_size = 850
            chunks = [p[i : i + chunk_size] for i in range(0, len(p), chunk_size)]
            num_chunks = len(chunks) - 1
            # find this value in props.conf and chunk accordingly
            for i in range(num_chunks, -1, -1):
                ar.logger.info(
                    ":::playbooks:{}:{}:{}:::".format(random_guid, "%02d" % (i,), chunks[i])
                )
            config.logger.info("Done pushing playbooks")
            ar.logger.info(f":::severities:{s}:::")
            config.logger.info("Done pushing severities")

        return {"success": True, "status": 200}


class PhantomWorkbooks(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        self.session_key = None
        self.config = None
        self.payload = None
        self.workbooks = None
        self.sync_key = None
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, args):
        request = json.loads(args)
        method = request["method"]
        endpoint = request.get("path_info")
        payload = request.get("payload", {})
        self.session_key = request["session"]["authtoken"]
        try:
            self.config = PhantomConfig(COMPONENT, self.session_key)
        except Exception as e:
            contents = {"status": 200, "success": False, "error": e}
            return json.dumps({"payload": contents, "status": contents.get("status")})

        if method == "POST":
            try:
                self.workbooks = json.loads(payload.get("workbooks"))
                self.sync_key = json.loads(payload.get("sync_key"))
            except:
                self.workbooks = json.loads(payload).get("workbooks", {})
                self.sync_key = json.loads(payload).get("sync_key", {})
            contents = self.handle_POST()
        elif method == "GET":
            self.sync_key = endpoint
            contents = self.handle_GET()
        else:
            contents = {"error": "Invalid or missing arguments", "status": 404}

        return json.dumps({"payload": contents, "status": contents.get("status")})

    def get_default_server(self, server_configs):
        non_default_servers = []
        default_server = None
        for cur_config in server_configs:
            default = str(server_configs[cur_config].get("default", "")).lower()
            if default.lower() == "default" or default == "true":
                default_server = server_configs[cur_config]
            else:
                non_default_servers.append(server_configs[cur_config])
        return default_server, non_default_servers

    def create_workbook_template(self, server, last_sync_set):
        workbook_templates = {}
        self.config.logger.debug(
            "Attempting to retrieve workbook templates for '{}'".format(server.get("custom_name"))
        )
        if not server.get("server", "").lower().startswith("https://"):
            self.config.logger.error(server.get("server", SERVER_MISSING))
            raise Exception("SOAR only supports https, please update your server config.")
        try:
            if not server.get("ph-auth-token"):
                raise PasswordStoreException(
                    "Failed to load auth token from credential store. User needs permission to access storage/passwords."
                )
            if not server.get("arrelay"):
                server["arrelay"] = False
            server["ph-auth-token"] = unquote(server.get("ph-auth-token"))
            pi = PhantomInstance(
                server,
                self.config.logger,
                verify=self.config[VERIFY_KEY],
                fips_enabled=self.config.fips_is_enabled,
            )
            workbook_templates, err = pi.get_workbook_template(last_sync_set)
            if err is not None:
                return {
                    "error": {"custom_name": json.dumps(server.get("custom_name")), "message": err},
                    "status": 400,
                }

            workbook_phase_templates, err = pi.get_workbook_phase_template()
            for wt_key, wt_value in workbook_templates.items():
                str_id = str(wt_value.get("id"))
                try:
                    # If there are no phases for the template, then keep it as an empty list []
                    workbook_templates[wt_key]["phases"] = workbook_phase_templates[str_id]
                except:
                    pass
            return workbook_templates
        except Exception as e:
            return {
                "error": {
                    "custom_name": json.dumps(server.get("custom_name")),
                    "message": "Error retrieving workbooks for {}. {}".format(
                        self.config.get("custom_name"), str(e)
                    ),
                },
                "status": 400,
            }

    def sort_post_template(self, workbook_template):
        deleted = [
            workbook_template[item]
            for item in workbook_template
            if workbook_template[item]["status"] == "deleted"
        ]
        not_deleted = [
            workbook_template[item]
            for item in workbook_template
            if workbook_template[item]["status"] != "deleted"
        ]
        return deleted, not_deleted

    def validate_server_connection(self, server):
        try:
            if not server.get("server", "").lower().startswith("https://"):
                self.config.logger.error(server.get("server", SERVER_MISSING))
                raise Exception("SOAR only supports https, please update your server config.")
            if not server.get("ph-auth-token"):
                raise PasswordStoreException(
                    "Failed to load auth token from credential store. User needs permission to access storage/passwords."
                )
            if not server.get("arrelay"):
                server["arrelay"] = False
            server["ph-auth-token"] = unquote(server.get("ph-auth-token"))
            pi = PhantomInstance(
                server,
                self.config.logger,
                verify=self.config[VERIFY_KEY],
                fips_enabled=self.config.fips_is_enabled,
            )
            contains, cef_metadata = pi.verify_server()
            self.config.logger.info("Connection to '{}' is valid".format(server.get("custom_name")))
            return True, None
        except Exception as e:
            self.config.logger.info(
                "Connection to '{}' is not valid. Cannot sync workbooks. Error: {}".format(
                    server.get("custom_name"), e
                )
            )
            return False, str(e)

    def get_server_statuses(self, servers_available):
        # Can only sync workbooks for servers that are up and running. Others will be skipped
        available_servers = {}
        unavailable_servers = {}
        for server in servers_available:
            is_live, message = self.validate_server_connection(servers_available[server])
            if is_live is True:
                available_servers[servers_available[server].get("ph_auth_config_id")] = (
                    servers_available[server]
                )
            else:
                tmp = servers_available[server]
                tmp.update({"error_message": message})
                unavailable_servers[servers_available[server].get("ph_auth_config_id")] = tmp
        return available_servers, unavailable_servers

    def sanitize_workbook(self, workbook, additional_factors=[]):
        tmp_default_workbook = deepcopy(workbook)
        nondetermining_factors = [
            "_originating_server",
            "id",
            "template",
            "phase",
            "creator",
            "_original_name",
        ] + additional_factors
        if workbook is None:
            return False
        for item in nondetermining_factors:
            try:
                del tmp_default_workbook[item]
            except:
                pass
            phases = workbook.get("phases")
            len_phases = 0
            if phases:
                len_phases = len(phases)
            for phase_item in range(len_phases):
                tmp_default_workbook["phases"][phase_item].pop(item, None)
                for task_item in range(len(workbook["phases"][phase_item]["tasks"])):
                    tmp_default_workbook["phases"][phase_item]["tasks"][task_item].pop(item, None)
        return tmp_default_workbook

    def create_unique_workbook(
        self, original_workbook, incoming_workbook, workbook_names, last_sync_workbook_names
    ):
        workbook_to_post = dict()
        name = None
        _original_name = None
        if incoming_workbook is None and original_workbook:
            workbook_to_post[original_workbook["name"]] = original_workbook
            return workbook_to_post
        name = incoming_workbook.get("name")
        _original_name = incoming_workbook.get("_original_name")
        # Can be same name here too
        if original_workbook is None and name not in last_sync_workbook_names:
            workbook_to_post[name] = incoming_workbook
            workbook_to_post[name]["is_default"] = False
            return workbook_to_post
        if original_workbook is None and name in last_sync_workbook_names:
            updates = {
                "is_default": False,
                "prev_state": incoming_workbook["status"],
                "status": "deleted",
            }
            workbook_to_post[name] = incoming_workbook
            workbook_to_post[name].update(updates)
            return workbook_to_post
        default_new_workbook = self.sanitize_workbook(original_workbook)
        current_workbook = self.sanitize_workbook(incoming_workbook)
        is_same = default_new_workbook == current_workbook
        # name = original_workbook.get('name')
        if (
            original_workbook and name in last_sync_workbook_names
        ) or _original_name in last_sync_workbook_names:
            # True North!
            workbook_to_post[name] = original_workbook
            return workbook_to_post
        if is_same is True:
            # if is_same is True and name not in last_sync_workbook_names:
            workbook_to_post[name] = original_workbook
            if workbook_to_post[name].get("_originating_server") is None:
                workbook_to_post[name]["_originating_server"] = []
            workbook_to_post[name]["_originating_server"] += incoming_workbook.get(
                "_originating_server", []
            )
        else:
            if _original_name:
                name = _original_name
            count = 1
            new_name = f"{name}_{count}"
            all_existing_names = workbook_names.union(last_sync_workbook_names)
            while new_name in all_existing_names:
                count += 1
                new_name = f"{name}_{count}"
            updates = {
                "is_default": False,
                "name": new_name,
                "_original_name": name,
                "status": "deleted",
            }
            if incoming_workbook["status"] != "deleted":
                updates.update({"prev_state": incoming_workbook["status"]})
            workbook_to_post[new_name] = incoming_workbook
            workbook_to_post[new_name].update(updates)
            workbook_to_post[new_name].pop("_originating_server", None)
        return workbook_to_post

    # When you delete a workbook_template, its following phases and tasks will also be deleted. So, you just need to do
    # curl -ku admin:password https://10.1.18.147/rest/workbook_template/11 -X DELETE
    def handle_GET(self, key=None):
        import time

        results = dict()
        # config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            new_workbooks = {}
            servers_available = get_safe(self.config, PHANTOM_KEY, {})
            self.config.logger.info("Retrieving workbook templates from SOAR server(s)...")

            available_servers, unavailable_servers = self.get_server_statuses(servers_available)
            self.config.logger.info(f"Available servers: {available_servers}")
            self.config.logger.info(f"Unavailable servers: {unavailable_servers}")
            for item in available_servers:
                results[available_servers[item].get("ph_auth_config_id")] = {
                    "verified_connection": True
                }
            for item in unavailable_servers:
                results[unavailable_servers[item].get("ph_auth_config_id")] = {
                    "verified_connection": False,
                    "error_message": unavailable_servers[item].get("error_message"),
                }

            last_sync_workbooks = get_safe(self.config, f"{WORKBOOK_KEY}", {})
            default_server, non_default_servers = self.get_default_server(available_servers)

            # get the data from the default server. this is the main workbook info that all other servers should follow
            if default_server:
                self.config.logger.info(
                    "Default server is '{}'".format(default_server.get("custom_name"))
                )
                new_workbooks = self.create_workbook_template(
                    default_server, set(last_sync_workbooks.keys())
                )
                if new_workbooks.get("error") is not None:
                    return {
                        "error": "Error connecting to default server: {}".format(
                            new_workbooks.get("error")
                        ),
                        "status": 400,
                    }
                # Check for duplicate named workbooks
                # for item in new_workbooks
            else:
                for item in unavailable_servers:
                    if str(unavailable_servers[item].get("default")).lower() in [
                        "true",
                        "default",
                    ] and unavailable_servers[item].get("error_message"):
                        message = "Could not verify connection to default server. Please ensure connection to SOAR server is working and that user is enabled."
                        return {
                            "error": message,
                            "error_additional": "Error: {}".format(
                                unavailable_servers[item].get("error_message")
                            ),
                            "status": 200,
                            "success": 403,
                        }
                return {
                    "error": "No default server selected or enabled. Please set a default server under SOAR Server Configuration and verify that the user is enabled in SOAR.",
                    "status": 400,
                }

            ## TODO: testing ###
            # for item in new_workbooks:
            #     self.config.logger.info("     item: {}, status={}, server={}".format(item, new_workbooks[item].get('status'), new_workbooks[item].get('_originating_server')))

            for cur_config in non_default_servers:
                keys = set(last_sync_workbooks.keys()).union(set(new_workbooks.keys()))
                workbook_templates = self.create_workbook_template(cur_config, keys)
                for item in workbook_templates:
                    existing_names = set(new_workbooks.keys())
                    workbook_to_post = self.create_unique_workbook(
                        new_workbooks.get(item),
                        workbook_templates[item],
                        existing_names,
                        last_sync_workbooks.keys(),
                    )
                    new_workbooks.update(workbook_to_post)

            # Don't get rid of the deleted workbooks in conf
            for item in last_sync_workbooks:
                if (
                    new_workbooks.get(item)
                    and last_sync_workbooks[item].get("status") == "deleted"
                    and new_workbooks.get(item, {}).get("status") in {"deleted", None}
                ):
                    new_workbooks[item] = last_sync_workbooks[item]
                    new_workbooks[item].update({"is_default": False})
                    new_workbooks[item].pop("_originating_server", None)
                elif new_workbooks.get(item) is None:
                    new_workbooks[item] = last_sync_workbooks[item]
                    if last_sync_workbooks[item]["status"] != "deleted":
                        updates = {
                            "is_default": False,
                            "status": "deleted",
                            "prev_state": last_sync_workbooks[item]["status"],
                        }
                        new_workbooks[item].update(updates)
                    if new_workbooks.get(item, {}).get("id") == last_sync_workbooks.get(
                        item, {}
                    ).get("id"):
                        new_workbooks[item].pop("_originating_server", None)

            # self.config.logger.info("FINAL workbooks:")
            # for item in new_workbooks:
            #     self.config.logger.info("  item: {}, status={}, prev_state={}, s={}".format(item, new_workbooks[item].get('status'),new_workbooks[item].get('prev_state'), new_workbooks[item].get('_originating_server')))

            try:
                self.config[WORKBOOK_KEY] = new_workbooks
                time_now = int(time.time())
                self.config.update_workbook(WORKBOOK_LAST_SYNC_TIME, time_now)
            except splunk.AuthorizationFailed:
                raise Exception(SERVER_PERMISSIONS_ERROR)

            # # Now that you have the set of workbooks, sync it up with all the servers
            num_servers = len(available_servers)
            count = 0
            deleted_post_data, not_deleted_post_data = self.sort_post_template(new_workbooks)
            for server in available_servers:
                count += 1
                self.config.logger.debug(f"Count: {count}; Number of servers: {num_servers}")
                key = None if count < num_servers else self.sync_key
                pi = PhantomInstance(
                    available_servers[server],
                    self.config.logger,
                    verify=self.config[VERIFY_KEY],
                    fips_enabled=self.config.fips_is_enabled,
                )
                success, errors, sync, sync_key = pi.update_workbook_template_delete(
                    deleted_post_data, key
                )
                success, errors, sync, sync_key = pi.update_workbook_template(
                    not_deleted_post_data, key
                )
                results[server]["success"] = success
                results[server]["errors"] = errors
                if sync == "sync_key":
                    self.config.update_workbook(WORKBOOK_SYNC_KEY, sync_key)

            overall_success = True
            for item in results:
                if results[item].get("success") is not True:
                    overall_success = False

            return {"success": overall_success, "status": 200, "value": results}
        except Exception as e:
            msg = format_exc()
            self.config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }

    def parse_tmp_value(self, content):
        tmp_value = content.get("entry", [])[0].get("content", {}).get("tmp_value", {})
        if tmp_value == "{}":
            tmp_value = {}
        return tmp_value

    def handle_POST(self):
        results = {}
        # config = PhantomConfig(COMPONENT, self.sessionKey)
        try:
            self.config.logger.info("Posting SOAR workbooks to phantom.conf...")
            last_sync_workbooks = get_safe(self.config, f"{WORKBOOK_KEY}", {})
            servers_available = get_safe(self.config, PHANTOM_KEY, {})
            logging_key = get_safe(self.config, LOGGING_CONFIG, "DEBUG")
            self.config.update_log_level(logging_key)

            incoming_workbooks = {}
            for item in self.workbooks:
                new_name = unquote(json.loads(unquote(json.dumps(item))))
                incoming_workbooks[new_name] = self.workbooks[item]
                incoming_workbooks[new_name]["name"] = new_name

            available_servers, unavailable_servers = self.get_server_statuses(servers_available)
            self.config.logger.info(f"Available servers: {available_servers}")
            self.config.logger.info(f"Unavailable servers: {unavailable_servers}")
            for item in available_servers:
                results[available_servers[item].get("ph_auth_config_id")] = {
                    "verified_connection": True
                }
            for item in unavailable_servers:
                results[unavailable_servers[item].get("ph_auth_config_id")] = {
                    "verified_connection": False
                }

            default_server, non_default_servers = self.get_default_server(available_servers)

            # get the data from the default server. this is the main workbook info that all other servers should follow
            default_workbooks = {}
            if default_server:
                self.config.logger.info(
                    "Default server is '{}'".format(default_server.get("custom_name"))
                )
                default_workbooks = self.create_workbook_template(
                    default_server, set(last_sync_workbooks.keys())
                )
                if default_workbooks.get("error") is not None:
                    return {
                        "error": "Error connecting to default server: {}".format(
                            default_workbooks.get("error")
                        ),
                        "status": 200,
                    }
            else:
                for item in unavailable_servers:
                    if str(unavailable_servers[item].get("default")).lower() in {
                        "true",
                        "default",
                    } and unavailable_servers[item].get("error_message"):
                        self.config.logger.info("Default server not available")
                        message = "Could not verify connection to default server. Please ensure connection to SOAR server is working and that user is enabled."
                        return {
                            "error": message,
                            "error_additional": "Error: {}".format(
                                unavailable_servers[item].get("error_message")
                            ),
                            "status": 200,
                            "success": 403,
                        }
                return {
                    "error": "No default server selected or enabled. Please set a default server under SOAR Server Configuration and verify that the user is enabled in SOAR.",
                    "status": 200,
                }

            default_dup_keys = set(default_workbooks.keys())
            # make sure all incoming new workbooks are unique
            new_workbooks = deepcopy(last_sync_workbooks)
            for item in default_workbooks:
                workbook_to_post = self.create_unique_workbook(
                    default_workbooks[item],
                    last_sync_workbooks.get(item),
                    set(default_workbooks.keys()),
                    set(last_sync_workbooks.keys()),
                )
                new_workbooks.update(workbook_to_post)
                if last_sync_workbooks.get(item) is None:
                    default_dup_keys.update(item)

            new_and_default = deepcopy(new_workbooks)
            workbooks_to_update = {}
            workbooks_to_update.update(new_and_default)

            # Apply updates from PAOS UI
            for item in last_sync_workbooks:
                incoming_status = incoming_workbooks[item]["status"]
                if workbooks_to_update.get(item) is None:
                    workbooks_to_update[item] = last_sync_workbooks[item]
                if incoming_status == "purge":
                    workbooks_to_update[item]["status"] = "deleted"
                elif incoming_status == "deleted":
                    prev_data = workbooks_to_update[item]
                    if prev_data["status"] != "deleted":
                        workbooks_to_update[item]["prev_state"] = prev_data["status"]
                        workbooks_to_update[item]["status"] = "deleted"
                elif default_workbooks.get(item) is None:
                    # status incoming is published/draft, ---> status deleted
                    prev_data = workbooks_to_update[item]
                    if prev_data["status"] != "deleted":
                        workbooks_to_update[item]["prev_state"] = prev_data["status"]
                        workbooks_to_update[item]["status"] = "deleted"
                    elif incoming_status not in {"deleted", None}:
                        if (
                            prev_data.get("prev_state") is None
                            or prev_data.get("prev_state") == "deleted"
                        ):
                            workbooks_to_update[item]["status"] = "published"
                        else:
                            workbooks_to_update[item]["status"] = prev_data["prev_state"]
                        workbooks_to_update[item].pop("prev_state", None)
                        workbooks_to_update[item].pop("_originating_server", None)
                elif incoming_status not in {"deleted", None}:
                    prev_data = workbooks_to_update[item]
                    if prev_data.get("prev_state"):
                        workbooks_to_update[item]["status"] = prev_data["prev_state"]
                        workbooks_to_update[item].pop("prev_state", None)
                        workbooks_to_update[item].pop("_originating_server", None)

            for cur_config in non_default_servers:
                workbook_templates = self.create_workbook_template(
                    cur_config, set(last_sync_workbooks.keys())
                )
                for item in workbook_templates:
                    # existing_names = set(workbooks_to_update.keys())
                    # keys = set(last_sync_workbooks.keys()).union(set(workbooks_to_update.keys()))
                    workbook_to_post = self.create_unique_workbook(
                        workbooks_to_update.get(item),
                        workbook_templates[item],
                        default_dup_keys,
                        set(last_sync_workbooks.keys()),
                    )
                    workbooks_to_update.update(workbook_to_post)

            # Workbooks to post, removing the purged workbooks
            workbooks_to_post = deepcopy(workbooks_to_update)
            for item in workbooks_to_update:
                if incoming_workbooks.get(item, {}).get("status") == "purge":
                    workbooks_to_post.pop(item)

            deleted_post_data, not_deleted_post_data = self.sort_post_template(workbooks_to_update)
            self.config.logger.debug(f"Number workbooks total: {len(workbooks_to_update)}")
            for server in available_servers:
                pi = PhantomInstance(
                    available_servers[server],
                    self.config.logger,
                    verify=self.config[VERIFY_KEY],
                    fips_enabled=self.config.fips_is_enabled,
                )
                if deleted_post_data:
                    success, errors, _, _ = pi.update_workbook_template_delete(deleted_post_data)
                if not_deleted_post_data:
                    success, errors, _, _ = pi.update_workbook_template(not_deleted_post_data)
                results[server]["success"] = success
                results[server]["errors"] = errors

            # Post to conf file
            try:
                self.config[WORKBOOK_KEY] = workbooks_to_post
            except splunk.AuthorizationFailed:
                raise Exception(SERVER_PERMISSIONS_ERROR)

            overall_success = True
            for item in results:
                if results[item].get("success") is not True:
                    overall_success = False

            # Perform Sync Workbooks
            key = f"/{self.sync_key}"
            success, content = self.config.splunk.workbooks(key)
            content = json.loads(content.decode())
            for c in content.get("entry", []):
                if c.get("title") == "value":
                    value_content = c.get("content", {})
                    for value_item in value_content:
                        if results[value_item].get("verified_connection"):
                            results[value_item]["success"] = (
                                results[value_item]["success"]
                                and value_content[value_item]["success"]
                            )
                            all_errors = (
                                results[value_item]["errors"] + value_content[value_item]["errors"]
                            )
                            results[value_item]["errors"] = all_errors

            return {"success": overall_success and success, "status": 200, "value": results}
        except Exception as e:
            msg = format_exc()
            self.config.logger.error(msg)
            return {
                "error": str(e),
                "status": 400,
            }


# Need to make this output a JSON not a ini. Also export searches/datamodels.
# class DownloadConfig(BaseRestHandler):
#    def __init__(self, *args):
#        BaseRestHandler.__init__(self, *args)
#
#    def handle_GET(self):
#        try:
#            config = PhantomConfig(COMPONENT, self.sessionKey)
#            self.response.write(str(config))
#            self.response.setHeader('Content-Disposition', 'attachment; filename="phantom_config.json"')
#            return
#        except Exception as e:
#            msg = format_exc()
#            config.logger.error(msg)
#            return {
#                'error': str(e),
#                'status': 400,
#            }
