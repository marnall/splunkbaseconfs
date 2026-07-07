# File: phantom_command.py
# Copyright (c) 2016-2026 Splunk Inc.
#
# SPLUNK CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Splunk Inc. is PROHIBITED.

import json
import os
import sys

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication

# PersistentServerConnectionApplication needs sys.path setup before importing ta_addonphantom_declare
_SPLUNK_BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
if _SPLUNK_BIN_DIR not in sys.path:
    sys.path.insert(0, _SPLUNK_BIN_DIR)

import ta_addonphantom_declare  # noqa: F401

from phantom_config import PhantomConfig


COMPONENT = "configuration"

EVENT_FORWARDING_CONFIGS_QUERY = "rest /servicesNS/nobody/phantom/configs/conf-phantom | search eai:acl.app=phantom | search NOT title IN (accepted, artifact_ar, enable_logging, field_mapping, phantom, phantom_ar, playbooks_ar, verify_certs, version, workbooks, playbooks, severities, severities_ar) | fields title, value"

UPSERT_DATA_FORWARDING_ENDPOINT = "/servicesNS/nobody/phantom/upsert_data_forwarding"


class EventForwardingMigration(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        self.session_key = None
        self.config = None
        self.forwarding_configs = None
        super(PersistentServerConnectionApplication, self).__init__()

    def get_event_forwarding_configs(self):
        _, content = self.config.splunk.search({"search": EVENT_FORWARDING_CONFIGS_QUERY})
        return content

    def handle(self, args):
        request = json.loads(args)
        method = request["method"]
        endpoint = request.get("path_info")
        payload = request.get("payload", {})
        self.session_key = request["session"]["authtoken"]
        try:
            self.config = PhantomConfig(COMPONENT, self.session_key)
            self.config.logger.info("Event Forwarding Migration started.")
        except Exception as e:
            contents = {"status": 200, "success": False, "error": e}
            return json.dumps({"payload": contents, "status": contents.get("status")})

        self.config.logger.info("Validating saved searches")
        forwarding_configs = self.get_event_forwarding_configs()
        results = {}
        for item_str in forwarding_configs.splitlines():
            item = json.loads(item_str)
            result = item.get("result")
            config_id = result.get("title")
            values_str = result.get("value", {})
            values = json.loads(values_str)
            name = values.get("_name")
            self.config.logger.info(f"Working on {name} with values {values}")
            try:
                success, _ = self.config.splunk.post(
                    UPSERT_DATA_FORWARDING_ENDPOINT, params={"data": json.dumps(values)}
                )
                if success:
                    results[config_id] = {"name": name, "success": True}
            except Exception as e:
                self.config.logger.info(f"Error migrating {config_id} to alert action. {e}")
                results[config_id] = {"name": name, "success": False, "error": str(e)}

        contents = {"status": 200, "success": True, "results": results}

        return json.dumps({"payload": contents, "status": contents.get("status")})
