#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import json
import sys
import time
import platform
import traceback
import base64
import os
import os.path

import import_declare_test  # noqa: F401
import solnlib
from crowdstrike_fdr_ta_lib import config_builders, splunk_helpers, sqs_manager
from crowdstrike_fdr_ta_lib.constants import SESSION_KEY, SERVER_URI
from crowdstrike_fdr_ta_lib.abort_signal import abort_signal_handler_setup, is_aborted
from crowdstrike_fdr_ta_lib.logger_adapter import ModinputLoggerProxy

from splunklib import modularinput as smi
from typing import Union, Dict, Any

logger = ModinputLoggerProxy("sqs_based_manager")


class SqsBasedManager(smi.Script):
    def get_scheme(self) -> smi.Scheme:
        scheme = smi.Scheme("Crowdstrike FDR SQS based manager")
        scheme.description = (
            "This modular input does not consume any information for an indexer. "
            "It's responsible for getting SQS notifications about newly uploaded event batches, "
            "validating batch content and distributing ingestion of S3 located event files between "
            "managed inputs (workers)"
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
                "aws_sqs_url",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "aws_sqs_ignore_before",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "aws_sqs_visibility_timeout",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "cs_event_encoding",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "cs_ithr_type",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "cs_event_filter_name",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "cs_device_field_filter_name",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_external_events",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "index_for_external_events",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_ztha_events",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "index_for_ztha_events",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_inventory_aidmaster",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "index_for_aidmaster_events",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_inventory_managedassets",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "index_for_managedassets_events",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_inventory_notmanaged",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "index_for_notmanaged_events",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_inventory_appinfo",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "index_for_appinfo_events",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "collect_inventory_userinfo",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "index_for_userinfo_events",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "checkpoint_type",
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

    @splunk_helpers.use_conf("splunk_ta_crowdstrike_fdr_cs_event_filters")
    @splunk_helpers.use_conf("splunk_ta_crowdstrike_fdr_aws_collections")
    @splunk_helpers.use_conf("splunk_ta_crowdstrike_fdr_settings")
    @splunk_helpers.unpack_single_instance_input_conf(resolve_passwords=False)
    def stream_events(
        self,
        inputs: Dict[str, Any],
        ew: smi.EventWriter,
        metadata: Dict[str, Any],
        stanza: str,
        config: Dict[str, Any],
    ) -> None:
        sqs_manager_journal = None
        start_time = time.time()
        logger.debug(f"stream_events for stanza {stanza} has started")

        try:
            token = metadata[SESSION_KEY]
            server_uri = metadata[SERVER_URI]

            ta_settings = self.splunk_ta_crowdstrike_fdr_settings.all()
            loglevel = ta_settings.get("logging", {}).get("loglevel", "INFO")
            logger.set_modinput_loglevel(loglevel)

            fdr_aws_collection = self.splunk_ta_crowdstrike_fdr_aws_collections.all()
            cs_filters = self.splunk_ta_crowdstrike_fdr_cs_event_filters.all()

            input_config = config_builders.build_input_run_config(
                config, metadata, cs_filters, ew
            )

            consumer_config = config_builders.build_shared_config(config)
            aws_config = config_builders.build_aws_run_config(
                config, fdr_aws_collection
            )
            aws_proxy_cfg = config_builders.build_aws_proxy_config(ta_settings)
            aws_config["sqs_creds"].update(aws_proxy_cfg)
            aws_config["s3_creds"].update(aws_proxy_cfg)

            logger.info(f"{stanza} consumer_config: {consumer_config}")

            def stopper_fn() -> bool:
                if is_aborted():
                    logger.debug(f"{stanza} process is stopping as it has been aborted")
                    return True

                return False

            sqs_manager_journal = sqs_manager.SqsManager(
                server_uri, token, input_config, aws_config, stopper_fn
            )

            sqs_manager_journal.register(True, data=json.dumps(consumer_config))

            abort_signal_handler_setup()
            sqs_manager_journal.run()

        except Exception as e:
            msg = f"stream_events: cs_input_stanza={stanza}, error='{e}'"
            tb = " ---> ".join(traceback.format_exc().split("\n"))
            solnlib.log.log_exception(
                logger, e, "SQS Manager Error", msg_before=f"{msg} {tb}"
            )
        finally:
            if sqs_manager_journal and sqs_manager_journal.is_registered:
                sqs_manager_journal.unregister()
            logger.info(
                f"stream_events: cs_input_stanza={stanza}, exiting after {time.time()-start_time} seconds"
            )


if __name__ == "__main__":
    exit_code = SqsBasedManager().run(sys.argv)
    sys.exit(exit_code)
