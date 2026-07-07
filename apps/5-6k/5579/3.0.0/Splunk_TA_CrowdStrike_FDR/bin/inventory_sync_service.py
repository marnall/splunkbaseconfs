#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import csv
import os
import shutil
import sys
import tempfile
import time
import traceback

import import_declare_test  # noqa: F401
import solnlib

from typing import Optional, Union, Dict, Any
from crowdstrike_fdr_ta_lib import splunk_helpers
from crowdstrike_fdr_ta_lib.logger_adapter import ModinputLoggerProxy
from crowdstrike_fdr_ta_lib.constants import (
    APP_NAME,
    HOST_RES_COLLECTION_NAME,
    HOST_RES_LOCAL_COLLECTION_CSV,
)
from splunklib import binding, client
from splunklib import modularinput as smi

logger = ModinputLoggerProxy("inventory_sync_service")


CSV_FIELD_NAMES = [
    "aid",
    "ComputerName",
    "AgentLocalTime",
    "City",
    "Continent",
    "Country",
    "MachineDomain",
    "OU",
    "SiteName",
    "SystemProductName",
    "Time",
    "Timezone",
    "Version",
    "event_platform",
    "GatewayIP",
    "GatewayMAC",
    "LocalAddressIP4",
    "MAC",
]


class INVENTORY_SYNC_SERVICE(smi.Script, splunk_helpers.CSScriptHelper):
    def __init__(self) -> None:
        super(INVENTORY_SYNC_SERVICE, self).__init__()

    def get_scheme(self) -> smi.Scheme:
        scheme = smi.Scheme("Crowdstrike FDR inventory sync service")
        scheme.description = (
            "This modular input does not consume any information for an indexer. "
            "It is requred to periodically update heavy forwarder with host information "
            "located at a search head in a form of KV store collection. "
            "Crowdstrike FDR TA requires host information for index time host resolution. "
            "If this modular input is not configured host reaolution will take place at search time only. "
            "IMPORTANT: DO NOT ENABLE MORE THEN ONE INPUT. DO NOT USE YOUR PERSONAL CREDENTIALS, "
            "REQUEST TECHNICAL USER TO BE CREATED"
        )

        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )

        scheme.add_argument(
            smi.Argument(
                "search_head_address",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "search_head_port",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "search_head_username",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "search_head_password",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "use_failover_search_head",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "failover_search_head_address",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "failover_search_head_port",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "failover_search_head_username",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "failover_search_head_password",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "run_only_one",
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition: Any) -> None:
        return

    def collect_connection_info(
        self, props: Dict[str, Any], prefix: str = "", stanza_pwds: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        logger.debug("collect_args, prefix: {}".format(prefix))

        pwd_prop_name = "{}{}".format(prefix, "search_head_password")
        pwd_prop_val = props.get(pwd_prop_name)
        if pwd_prop_val.count("*") == len(pwd_prop_val):
            pwd_prop_val = stanza_pwds.get(pwd_prop_name)

        info = dict(
            host=props.get("{}{}".format(prefix, "search_head_address")),
            port=props.get("{}{}".format(prefix, "search_head_port")),
            username=props.get("{}{}".format(prefix, "search_head_username")),
            password=pwd_prop_val,
            owner="nobody",
            app=APP_NAME,
        )

        return info

    def retrieve_collection(
        self, connection_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        try:
            service = client.connect(**connection_info)
            collection = service.kvstore[HOST_RES_COLLECTION_NAME]
            data = collection.data.query()
            if not data:
                msg = "Host information collection is empty at {host}:{port}"
                logger.warning(msg.format(**connection_info))
            return data
        except binding.AuthenticationError as e:
            msg = "Failed to authenticate to splunk instance {host}:{port}"
            solnlib.log.log_authentication_error(
                logger, e, msg_before=msg.format(**connection_info)
            )
            return None
        except Exception as e:
            msg = f"Unexpected error when retrieving kvstore collection: {e}"
            tb = " ---> ".join(traceback.format_exc().split("\n"))
            solnlib.log.log_exception(
                logger, e, "KVstore Error", msg_before=f"{msg} {tb}"
            )
            return None

    def get_ta_settings(self) -> Dict[str, Any]:
        return self.load_config(
            APP_NAME, "splunk_ta_crowdstrike_fdr_settings", "TA settings"
        )

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter) -> None:
        start_time = time.time()
        ta_settings = self.get_ta_settings()
        loglevel = ta_settings.get("logging", {}).get("loglevel", "INFO")
        logger.set_modinput_loglevel(loglevel)

        data = None
        for stanza, props in inputs.inputs.items():
            logger.configure_modinput_logger(stanza.replace("://", "."))
            stanza_pwds = self.get_app_stanza_passwords(APP_NAME, stanza)
            for sh_prefix, sh_type in zip(["", "failover_"], ["primary", "failover"]):
                info = self.collect_connection_info(props, sh_prefix, stanza_pwds)
                data = self.retrieve_collection(info)
                if data is None:
                    msg = "Failed to retrieve collection from the {} search head {host}:{port}"
                    logger.warning(msg.format(sh_type, **info))

                if props.get("use_failover_search_head") != "1":
                    break
            break

        if data is None:
            logger.warning("Failed to retrieve collection")
            return

        if isinstance(data, list) and len(data) == 0:
            logger.info(
                "Inventory collection is not synced as source collection is empty"
            )
            return

        if not isinstance(data, list) or not isinstance(data[0], dict):
            logger.warn(
                f"Inventory collection is not synced as source collection "
                f"has unexpected formatting: '{type(data[0])}', '{data[0]}'"
            )
            return

        try:
            temp_file = None
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, newline=""
            ) as temp_file:
                writer = csv.DictWriter(
                    temp_file, quoting=csv.QUOTE_ALL, fieldnames=CSV_FIELD_NAMES
                )
                writer.writeheader()
                for host in data:
                    row = {k: v for k, v in host.items() if k in CSV_FIELD_NAMES and v}
                    writer.writerow(row)
                file_size = temp_file.tell()

            try:
                csv_path = solnlib.splunkenv.make_splunkhome_path(
                    ["etc", "apps", APP_NAME, "lookups", HOST_RES_LOCAL_COLLECTION_CSV]
                )
                shutil.copy(temp_file.name, csv_path)
            except Exception as e:
                msg = f"Inventory collection final rewrite failed with traceback: {e}"
                solnlib.log.log_exception(
                    logger, e, "Inventory Collection Error", msg_before=msg
                )
                return

        except Exception as e:
            msg = f"Inventory collection save failed with error: {e}"
            tb = " ---> ".join(traceback.format_exc().split("\n"))
            solnlib.log.log_exception(
                logger, e, "Inventory Collection Error", msg_before=f"{msg} {tb}"
            )
            return
        finally:
            if temp_file is not None:
                os.remove(temp_file.name)

        msg = (
            "Inventory collection successfully synced. File size: {} bytes. "
            "Records count: {}. Time taken: {} seconds."
        )
        logger.info(msg.format(file_size, len(data), time.time() - start_time))


if __name__ == "__main__":
    exit_code = INVENTORY_SYNC_SERVICE().run(sys.argv)
    sys.exit(exit_code)
