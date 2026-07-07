#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
from typing import Union, Dict, Any

from splunklib import modularinput as smi
import sfdc_utility as su
from solnlib import log
import requests


def create_sfdc_util_from_inputs(
    inputs: smi.InputDefinition, log_file: str
) -> su.SFDCUtil:
    """Create SFDCUtil object from inputs

    :param inputs: InputDefinition object
    :param log_file: Log file name
    :return: SFDCUtil object
    """
    input_name = list(inputs.inputs.keys())[0]
    input_items_name = input_name.split("://")[1]
    input_items_type = input_name.split("://")[0]

    sfdc_util_ob = su.SFDCUtil(
        log_file=log_file, session_key=inputs.metadata["session_key"]
    )

    sfdc_util_ob.file_checkpoint_dir = inputs.metadata["checkpoint_dir"]
    sfdc_util_ob.input_items = inputs.inputs[input_name]
    sfdc_util_ob.input_items["name"] = input_items_name
    sfdc_util_ob.input_items["input_type"] = input_items_type

    return sfdc_util_ob


def get_session_data(sfdc_util_ob: su.SFDCUtil) -> Union[Dict[str, Any], None]:
    """Retrieve and validate Salesforce session data based on the authentication type.

    :param sfdc_util_ob: SFDCUtil object
    :return: Session data dict
    """

    session_data = {}
    if sfdc_util_ob.account_info["auth_type"] == "basic":
        response = sfdc_util_ob.login_sfdc()
        content = response.text

        if response.status_code != 200:
            fault_string, _ = sfdc_util_ob.handle_failed_login(content)
            log.log_connection_error(
                sfdc_util_ob.logger,
                requests.exceptions.HTTPError,
                msg_before=(
                    f"Login failed for salesforce account {sfdc_util_ob.account_info['username']} "
                    f"with reason {fault_string}"
                ),
            )
            return None

        sfdc_session_key = sfdc_util_ob.extract_session_id(content)
        if not sfdc_session_key:
            log.log_authentication_error(
                sfdc_util_ob.logger,
                Exception("No Session key URL"),
                msg_before=f"Unable to find the Salesforce Session Key for data collection. Exiting the invocation of input: {sfdc_util_ob.input_items['name']}",
            )
            return None

        sfdc_server_url = sfdc_util_ob.extract_server_url(content)
        if not sfdc_server_url:
            log.log_connection_error(
                sfdc_util_ob.logger,
                Exception("No Server URL found"),
                msg_before=f"Unable to find the Salesforce Server URL for data collection. Exiting the invocation of input: {sfdc_util_ob.input_items['name']}",
            )
            return None
        session_data["sfdc_session_key"] = sfdc_session_key
        session_data["sfdc_server_url"] = sfdc_server_url
        user_account_id = sfdc_util_ob.extract_user_account_id(content)

    else:
        sfdc_util_ob.account_info[
            "sfdc_server_url"
        ] = f"https://{sfdc_util_ob.account_info['endpoint']}"
        user_account_id = sfdc_util_ob.get_account_id()

    if user_account_id is None:
        log.log_configuration_error(
            sfdc_util_ob.logger,
            Exception("No Account Id Error"),
            msg_before=f"Unable to fetch the user Account Id for input '{sfdc_util_ob.input_items['name']}'",
        )

    session_data["user_account_id"] = user_account_id  # type: ignore

    return session_data
