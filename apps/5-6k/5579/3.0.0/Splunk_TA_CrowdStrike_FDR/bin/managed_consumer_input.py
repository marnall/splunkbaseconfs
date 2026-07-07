#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import sys
import time
import platform
import traceback
import base64
import os
import os.path

import import_declare_test  # noqa: F401
import solnlib
from crowdstrike_fdr_ta_lib import config_builders, managed_consumer, splunk_helpers
from crowdstrike_fdr_ta_lib.logger_adapter import ModinputLoggerProxy
from crowdstrike_fdr_ta_lib.constants import (
    SESSION_KEY,
    SERVER_URI,
    SOURCETYPE_SENSOR,
    DEVICE_API_HOST_RES_REFRESH_INTERVAL,
)
from crowdstrike_fdr_ta_lib.event_enricher import HostResolution
from crowdstrike_fdr_ta_lib.abort_signal import abort_signal_handler_setup, is_aborted
from splunklib import modularinput as smi
from typing import Optional, Union, Dict, Any

logger = ModinputLoggerProxy("sqs_based_manager")


class MANAGED_CONSUMER_INPUT(smi.Script):
    def __init__(self) -> None:
        super(MANAGED_CONSUMER_INPUT, self).__init__()

    def get_scheme(self) -> smi.Scheme:
        scheme = smi.Scheme("Crowdstrike FDR managed S3 consumer")
        scheme.description = "Crowdstrike FDR managed S3 consumer"
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
                "manager",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "per_file_exec",
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
    @splunk_helpers.use_conf("splunk_ta_crowdstrike_fdr_cs_device_field_filters")
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
        start_time = time.time()
        logger.debug(f"Starting managed consumer input {stanza}")

        manager = None
        consumer = None

        token = metadata[SESSION_KEY]
        server_uri = metadata[SERVER_URI]

        try:
            manager = "sqs_based_manager://" + config.get("manager")
            log_prefix = f"Executing managed consumer: cs_input_stanza={stanza} cs_manager={manager}"

            ta_settings = self.splunk_ta_crowdstrike_fdr_settings.all()
            loglevel = ta_settings.get("logging", {}).get("loglevel", "INFO")
            logger.set_modinput_loglevel(loglevel)

            logger.debug(log_prefix)

            aws_proxy_cfg = config_builders.build_aws_proxy_config(ta_settings)
            input_config = config_builders.build_consumer_config(config, metadata, ew)

            fdr_aws_collections = self.splunk_ta_crowdstrike_fdr_aws_collections.all()
            cs_event_filters = self.splunk_ta_crowdstrike_fdr_cs_event_filters.all()
            cs_field_filters = (
                self.splunk_ta_crowdstrike_fdr_cs_device_field_filters.all()
            )

            def stopper_fn() -> bool:
                if is_aborted():
                    logger.debug(
                        f"{stanza} process is stopping as it  has been aborted"
                    )
                    return True

                return False

            shared_config = None
            consumer_id = f"[{stanza}]@{input_config['server_host']}"
            consumer = managed_consumer.ManagedConsumer(
                server_uri, token, manager, stanza, consumer_id, stopper_fn
            )
            shared_config = consumer.register()

            if not shared_config:
                logger.warning(
                    f"{log_prefix}, shared_config={shared_config}, failed to get manager information, "
                    "make sure assigned manager input is enabled and running"
                )
                return

            logger.info(f"{log_prefix}: shared_config={shared_config}")

            input_config.update(shared_config)
            input_config.update(
                config_builders.build_filter_config(input_config, cs_event_filters)
            )

            device_field_filter = config_builders.build_device_field_filter_config(
                input_config, cs_field_filters
            )
            if input_config.get("cs_ithr_type") == "device_api":
                host_res = HostResolution(
                    server_uri,
                    token,
                    DEVICE_API_HOST_RES_REFRESH_INTERVAL,
                    **device_field_filter,
                )
                input_config["enrichers"] = {SOURCETYPE_SENSOR: host_res}

            aws_collection = shared_config.get("aws_collection")
            if not aws_collection:
                logger.warning(
                    f"{log_prefix}, AWS FDR collection name is not selected at manager config"
                )
                return

            aws_config = config_builders.extract_aws_credentials(
                aws_collection, fdr_aws_collections
            )
            aws_config.update(aws_proxy_cfg)

            logger.info(f"{log_prefix}: input_config: {input_config}")

            consumer.apply_configs(aws_config, input_config)

            abort_signal_handler_setup()
            consumer.run()

        except Exception as e:
            msg = f"{log_prefix}, error='{e}'"
            tb = " ---> ".join(traceback.format_exc().split("\n"))
            solnlib.log.log_exception(
                logger, e, "SQS Managed Consumer Error", msg_before=f"{msg} {tb}"
            )
        finally:
            if consumer and consumer.is_registered:
                consumer.unregister()

            logger.info(f"{log_prefix}, exiting after {time.time()-start_time} seconds")


if __name__ == "__main__":
    exit_code = MANAGED_CONSUMER_INPUT().run(sys.argv)
    sys.exit(exit_code)
