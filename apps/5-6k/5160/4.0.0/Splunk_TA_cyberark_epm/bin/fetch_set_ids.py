#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

import import_declare_test  # noqa
import splunk.admin as admin
import cyberark_epm_utils as utils
import cyberark_epm_connect
import json
from splunktaucclib.rest_handler.error import RestError
from cyberark_epm_utils import (
    add_ucc_error_logger,
)
from constants import CONFIGURATION_ERROR


class FetchSetIDs(admin.MConfigHandler):
    param = "account_name"

    def setup(self):
        self.supportedArgs.addOptArg(self.param)

    def handleList(self, conf_info):
        session_key = self.getSessionKey()
        logger = utils.set_logger(
            session_key, "splunk_ta_cyberark_epm_rh_fetch_set_ids"
        )
        try:
            if (
                not self.callerArgs
                or not self.callerArgs.get("account_name")
                or len(self.callerArgs.get("account_name")) <= 0
            ):
                raise Exception("Account is missing")
            account_name = self.callerArgs.get("account_name")[0]
            account_details = utils.get_account_details(
                logger, session_key, account_name
            )
            config = {
                "session_key": session_key,
                "input_params": None,
                "logger": logger,
            }
            config.update(account_details)
            config["proxies"] = utils.get_proxy_settings(logger, session_key)
            obj = cyberark_epm_connect.CyberarkConnect(config)
            obj.authenticate(is_request_from_ui=True)
            set_list = obj.get_sets_list()
            if len(set_list) == 0:
                raise Exception("Set ID list is empty")
            logger.info("Set IDs lists {}".format(set_list))
            logger.info(
                "Available list of all sets associated with this account {}".format(
                    set_list
                )
            )
            for each_set in set_list:
                conf_info[
                    "{} | {}".format(each_set.get("Name"), each_set.get("Id"))
                ].append("value", json.dumps(each_set))
            conf_info["All"].append("value", "All")

        except Exception as e:
            msg = "The selected account does not have any SetIds, please check your account configuration"
            add_ucc_error_logger(logger, CONFIGURATION_ERROR, e, msg_before=msg)
            conf_info[""].append("value", "")


def main():
    admin.init(FetchSetIDs, admin.CONTEXT_NONE)
