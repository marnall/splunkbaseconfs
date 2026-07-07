#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This file contains certain ignores for certain linters.

* isort ignores:
- isort: skip = Particular import must be the first import.

* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""
import traceback

import import_declare_test  # isort: skip # noqa: F401
import sys

from splunklib import modularinput as smi
import sfdc_consts as sc
import sfdc_utility as su
from data_collector.sfdc_object_data_collector import SfdcObjectDataCollector
from sfdc_modinputs_common import create_sfdc_util_from_inputs, get_session_data
from solnlib import log


class SFDC_OBJECT(smi.Script):
    def __init__(self):
        super(SFDC_OBJECT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("sfdc_object")
        scheme.description = "Salesforce Object"
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
                "account",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "object",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "object_fields",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "order_by",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "start_date",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "delay",
                required_on_create=False,
            )
        )

        return scheme

    def validate_input(self, definition: smi.ValidationDefinition) -> bool:
        return True

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter) -> None:
        sfdc_util_ob = create_sfdc_util_from_inputs(
            inputs, "splunk_ta_salesforce_sfdc_object"
        )
        sfdc_util_ob.logger = sfdc_util_ob.get_logger(
            f"splunk_ta_salesforce_sfdc_object_{su.get_hashed_value(sfdc_util_ob.input_items['name'])}"
        )
        sfdc_util_ob.logger.info(
            f"Starting the invocation of input '{sfdc_util_ob.input_items['name']}'"
        )

        try:
            if sfdc_util_ob.is_account_missing():
                return

            sfdc_util_ob.account_info = sfdc_util_ob.get_conf_data(
                sc.ACCOUNT_CONF_FILE, sfdc_util_ob.input_items["account"]
            )
            if not sfdc_util_ob.account_info:
                return

            sfdc_util_ob.account_info["name"] = sfdc_util_ob.input_items["account"]
            sfdc_util_ob.sslconfig = sfdc_util_ob.get_sslconfig()
            sfdc_util_ob.proxies = sfdc_util_ob.build_proxy_info()

            session_data = get_session_data(sfdc_util_ob)

            if not session_data:
                return

            sfdc_util_ob.account_info.update(session_data)

            object_collector = SfdcObjectDataCollector(sfdc_util_ob)
            object_collector.start()
        except Exception as e:
            log.log_exception(
                sfdc_util_ob.logger,
                e,
                "Object stream events Error",
                msg_before=(
                    f"Encountered an error: {e}.\nTraceback: {traceback.format_exc()}"
                ),
            )


if __name__ == "__main__":
    exit_code = SFDC_OBJECT().run(sys.argv)
    sys.exit(exit_code)
