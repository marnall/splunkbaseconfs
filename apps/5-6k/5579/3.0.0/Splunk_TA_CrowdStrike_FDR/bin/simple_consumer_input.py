#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import sys
import time
import traceback
import platform

import import_declare_test  # noqa: F401
import solnlib
from crowdstrike_fdr_ta_lib.event_enricher import HostResolution
from crowdstrike_fdr_ta_lib import config_builders, simple_consumer, splunk_helpers
from crowdstrike_fdr_ta_lib.logger_adapter import ModinputLoggerProxy
from crowdstrike_fdr_ta_lib.constants import (
    SESSION_KEY,
    SERVER_URI,
    SOURCETYPE_SENSOR,
    DEVICE_API_HOST_RES_REFRESH_INTERVAL,
)
from crowdstrike_fdr_ta_lib.abort_signal import (
    abort_signal_handler_setup,
    is_aborted,
    AbortSignalException,
)
from splunklib import modularinput as smi
from typing import Union, Dict, Any

logger = ModinputLoggerProxy("simple_consumer")


class SIMPLE_CONSUMER_INPUT(smi.Script):
    def __init__(self) -> None:
        super(SIMPLE_CONSUMER_INPUT, self).__init__()

    def get_scheme(self) -> smi.Scheme:
        scheme = smi.Scheme("Crowdstrike FDR Simple Consumer")
        scheme.description = "Crowdstrike FDR SQS based S3 simple consumer"
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
                "aws_collection",
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
        logger.debug(f"stream_events for stanza {stanza} has started")

        token = metadata[SESSION_KEY]
        server_uri = metadata[SERVER_URI]

        try:
            ta_settings = self.splunk_ta_crowdstrike_fdr_settings.all()
            loglevel = ta_settings.get("logging", {}).get("loglevel", "INFO")
            logger.set_modinput_loglevel(loglevel)

            fdr_aws_collection = self.splunk_ta_crowdstrike_fdr_aws_collections.all()
            cs_event_filters = self.splunk_ta_crowdstrike_fdr_cs_event_filters.all()
            cs_field_filters = (
                self.splunk_ta_crowdstrike_fdr_cs_device_field_filters.all()
            )

            input_config = config_builders.build_input_run_config(
                config, metadata, cs_event_filters, ew
            )

            device_field_filter = config_builders.build_device_field_filter_config(
                config, cs_field_filters
            )

            aws_config = config_builders.build_aws_run_config(
                config, fdr_aws_collection
            )
            aws_proxy_cfg = config_builders.build_aws_proxy_config(ta_settings)
            aws_config["sqs_creds"].update(aws_proxy_cfg)
            aws_config["s3_creds"].update(aws_proxy_cfg)

            if input_config.get("cs_ithr_type") == "device_api":
                host_res = HostResolution(
                    server_uri,
                    token,
                    DEVICE_API_HOST_RES_REFRESH_INTERVAL,
                    **device_field_filter,
                )
                input_config["enrichers"] = {SOURCETYPE_SENSOR: host_res}

            def stopper_fn() -> bool:
                if is_aborted():
                    logger.debug(f"{stanza} process is stopping as it has been aborted")
                    return True

                return False

            abort_signal_handler_setup()
            simple_consumer.run(input_config, aws_config, stopper_fn)
        except Exception as e:
            msg = f"stream_events: cs_input_stanza={stanza}, error='{e}'"
            tb = " ---> ".join(traceback.format_exc().split("\n"))
            solnlib.log.log_exception(
                logger, e, "SQS Simple Consumer Error", msg_before=f"{msg} {tb}"
            )
        finally:
            logger.info(
                f"stream_events: cs_input_stanza={stanza}, exiting after {time.time()-start_time} seconds"
            )


if __name__ == "__main__":
    exit_code = SIMPLE_CONSUMER_INPUT().run(sys.argv)
    sys.exit(exit_code)
