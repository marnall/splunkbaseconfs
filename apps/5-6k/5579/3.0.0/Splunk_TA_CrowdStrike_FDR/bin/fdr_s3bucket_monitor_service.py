#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import sys
import time
import traceback

import import_declare_test  # noqa: F401
import solnlib
from crowdstrike_fdr_ta_lib import aws_helpers, config_builders, splunk_helpers
from crowdstrike_fdr_ta_lib.constants import APP_NAME, SESSION_KEY, SERVER_URI
from crowdstrike_fdr_ta_lib.kvstore_collection import KVStoreCollection
from crowdstrike_fdr_ta_lib.logger_adapter import ModinputLoggerProxy
from splunklib import modularinput as smi

from typing import Union, Optional, Dict, Any

logger = ModinputLoggerProxy("fdr_s3bucket_monitor_service")


class FDR_S3BUCKET_MONITOR_SERVICE(smi.Script, splunk_helpers.CSScriptHelper):
    def __init__(self) -> None:
        super(FDR_S3BUCKET_MONITOR_SERVICE, self).__init__()

    def get_scheme(self) -> smi.Scheme:
        scheme = smi.Scheme("Crowdstrike FDR S3 bucket monitor")
        scheme.description = (
            "This is a diagnostic modinput. It monitors Crowdstrike dedicated S3 bucket and logs information "
            "about appearing FDR event batches. This information can then be compared with batches appeared"
            'in SQS messages to make sure there is no unknown consumer "stealing" SQS notifications'
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
                "aws_collection",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "aws_bucket",
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

    def get_fdr_aws_collection(
        self, session_key: Optional[str] = None
    ) -> Dict[str, Any]:
        return self.load_config(
            APP_NAME,
            "splunk_ta_crowdstrike_fdr_aws_collections",
            "FDR AWS collections",
            session_key,
        )

    def get_ta_settings(self, session_key: Optional[str] = None) -> Dict[str, Any]:
        return self.load_config(
            APP_NAME, "splunk_ta_crowdstrike_fdr_settings", "TA settings", session_key
        )

    def get_chekpointer(self, server_uri: str, token: str) -> KVStoreCollection:
        checkpointer = KVStoreCollection(
            server_uri, token, APP_NAME, "fdr_s3bucket_monitor_service_checkponter"
        )
        if not checkpointer.check_collection_exists():
            checkpointer.create_collection()
            checkpointer.define_collection_schema(
                {
                    "field.checkpoint_name": "string",
                    "field.checkpoint_value": "string",
                }
            )
        return checkpointer

    def get_checkpoint(
        self, checkpointer: KVStoreCollection, checkpoint_name: str
    ) -> Optional[str]:
        res = checkpointer.search_records({"checkpoint_name": checkpoint_name})
        if not res:
            return None
        return res[0]["checkpoint_value"]

    def set_checkpoint(
        self,
        checkpointer: KVStoreCollection,
        checkpoint_name: str,
        checkpoint_value: str,
    ) -> None:
        res = checkpointer.search_records({"checkpoint_name": checkpoint_name})
        data = {
            "checkpoint_name": checkpoint_name,
            "checkpoint_value": checkpoint_value,
        }
        if res:
            checkpointer.update_record(res[0]["_key"], data)
        else:
            checkpointer.create_record(data)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter) -> None:
        start_time = time.time()
        logger.info(
            "stream_events for modinput 'fdr_s3bucket_monitor_service' has started"
        )

        input_name = None
        try:
            token = inputs.metadata[SESSION_KEY]
            server_uri = inputs.metadata[SERVER_URI]

            input_items = []
            for input_name, input_item in inputs.inputs.items():
                input_item["input_stanza"] = input_name
                input_items.append((input_name, input_item))

            if not input_items:
                logger.info(f"stream_events: no configuration provided: {input_items}")
                return

            input_name, input_conf = input_items[0]

            ta_settings = self.get_ta_settings()
            loglevel = ta_settings.get("logging", {}).get("loglevel", "INFO")

            logger.configure_modinput_logger(input_name.replace("://", "."), loglevel)

            fdr_aws_collection = self.get_fdr_aws_collection()

            aws_config = config_builders.build_s3bucket_scan_config(
                input_conf, fdr_aws_collection
            )
            aws_proxy_cfg = config_builders.build_aws_proxy_config(ta_settings)
            aws_config["s3_creds"].update(aws_proxy_cfg)

            checkpointer = self.get_chekpointer(server_uri, token)

            timepoint = self.get_checkpoint(checkpointer, "fdr_s3_timepoint")
            next_timepoint = aws_helpers.aws_map_s3_bucket(
                aws_config["s3_creds"], aws_config["bucket"], timepoint
            )
            self.set_checkpoint(checkpointer, "fdr_s3_timepoint", next_timepoint)

        except Exception as e:
            msg = f"stream_events: cs_input_stanza={input_name}, traceback='{e}'"
            tb = " ---> ".join(traceback.format_exc().split("\n"))
            solnlib.log.log_exception(
                logger, e, "FDR S3 Bucket Monitor Error", msg_before=f"{msg} {tb}"
            )
        finally:
            logger.info(
                f"stream_events: cs_input_stanza={input_name}, exiting after {time.time()-start_time} seconds"
            )


if __name__ == "__main__":
    exit_code = FDR_S3BUCKET_MONITOR_SERVICE().run(sys.argv)
    sys.exit(exit_code)
