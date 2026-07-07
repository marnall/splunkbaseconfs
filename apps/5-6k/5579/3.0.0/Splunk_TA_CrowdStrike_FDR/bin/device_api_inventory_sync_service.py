#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import sys
import time
import traceback

from datetime import datetime, timezone

import import_declare_test  # noqa: F401
import solnlib

from splunklib import modularinput as smi
from typing import Union, Dict, Any

from crowdstrike_fdr_ta_lib import splunk_helpers, config_builders
from crowdstrike_fdr_ta_lib.constants import (
    SESSION_KEY,
    SERVER_URI,
    APP,
    DEVICE_API_HOST_RES_COLLECTION_NAME,
)
from crowdstrike_fdr_ta_lib.device_api_inventory_sync import DeviceApiInventorySync
from crowdstrike_fdr_ta_lib.logger_adapter import ModinputLoggerProxy

logger = ModinputLoggerProxy("device_api_inventory_sync_service")


class DEVICE_API_INVENTORY_SYNC_SERVICE(smi.Script):
    def __init__(self) -> None:
        super(DEVICE_API_INVENTORY_SYNC_SERVICE, self).__init__()

    def get_scheme(self) -> smi.Scheme:
        scheme = smi.Scheme("device_api_inventory_sync_service")
        scheme.description = (
            "This modular input does not consume any information for an indexer. "
            "As it runs it invokes CrowdStrike Device API to collect infomation about devices and stores it in internal KVStore collection to be used by ingesting modular inputs as part of host resolution process for sensor events. "
            "When running for the first time the modular input collects information about all the deveices. Every following run it will collect information only about the devices updated since the last check. "
            "To be able to share the same kvstore collection this modular input and ingesting modular inputs should run on the same Splunk host or in the same kvstore cluster for Splunk Enterprise and Cloud environments correspondingly."
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
                "api_client_id",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "api_client_secret",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "api_base_url",
                required_on_create=True,
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

    @splunk_helpers.use_checkpointer(
        "device_api_inventory_sync_service_checkponter", alias="checkpointer"
    )
    @splunk_helpers.use_conf("splunk_ta_crowdstrike_fdr_settings")
    @splunk_helpers.unpack_single_instance_input_conf(resolve_passwords=True)
    def stream_events(
        self,
        inputs: Dict[str, Any],
        ew: smi.EventWriter,
        metadata: Dict[str, Any],
        stanza: str,
        config: Dict[str, Any],
    ) -> None:
        start_time = time.time()
        logger.info(f"stream_events for input '{stanza}' has started.")

        timepoint = "Unknown"
        try:
            ta_settings = self.splunk_ta_crowdstrike_fdr_settings.all()
            loglevel = ta_settings.get("logging", {}).get("loglevel", "INFO")
            logger.set_modinput_loglevel(loglevel)

            cs_api_config = config_builders.build_crowdstrike_api_connection_config(
                config, ta_settings
            )

            checkpoint_name = f"crowdstrike_device_api_timepoint@{stanza}"
            timepoint = self.checkpointer.get(checkpoint_name)
            next_timepoint = datetime.now(timezone.utc).isoformat() + "Z"

            kvstore_api_config = dict(
                server_uri=metadata[SERVER_URI],
                token=metadata[SESSION_KEY],
                app=config[APP],
                name=DEVICE_API_HOST_RES_COLLECTION_NAME,
            )

            sync_service = DeviceApiInventorySync(cs_api_config, kvstore_api_config)
            sync_service.run(timepoint)

            timepoint = next_timepoint
            self.checkpointer.set(checkpoint_name, timepoint)

        except Exception as e:
            msg = f"stream_events: cs_input_stanza={stanza}, traceback='{e}'"
            tb = " ---> ".join(traceback.format_exc().split("\n"))
            solnlib.log.log_exception(
                logger, e, "Device API Inventory Sync Error", msg_before=f"{msg} {tb}"
            )
        finally:
            logger.info(
                f"stream_events: cs_input_stanza={stanza}, exiting after {time.time()-start_time} seconds, next_checkpoint={timepoint}"
            )


if __name__ == "__main__":
    exit_code = DEVICE_API_INVENTORY_SYNC_SERVICE().run(sys.argv)
    sys.exit(exit_code)
