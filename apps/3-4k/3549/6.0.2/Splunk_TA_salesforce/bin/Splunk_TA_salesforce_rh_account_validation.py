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
from typing import Dict, Any

from splunktaucclib.rest_handler.error import RestError

import import_declare_test  # isort: skip # noqa: F401
import traceback

import sfdc_utility as su
import sfdc_consts as sc
import splunk.admin as admin
from solnlib import log
from splunktaucclib.rest_handler.endpoint.validator import Validator


class AccountValidationError(Exception):
    pass


def account_validation(sfdc_util_ob: su.SFDCUtil, account_name: str) -> bool:
    """
    This function validate the account used for an input
    Raises RestError if any of the fields is invalid/incorrect
    :param sfdc_util_ob
    :param  account_name
    raises: RestError
    """
    sfdc_util_ob.logger.debug(
        f"Validating salesforce account credentials for account name {account_name}"
    )
    try:
        data = sfdc_util_ob.get_conf_data(sc.ACCOUNT_CONF_FILE, account_name)
        return _validate_account_credentials(data, sfdc_util_ob)
    except Exception as e:
        log.log_exception(
            sfdc_util_ob.logger,
            e,
            "Account validation Error",
            msg_before=f"Failed to read {sc.ACCOUNT_CONF_FILE} for account name {account_name}. Reason: {str(e)}",
        )
        raise RestError(400, str(e))


def _validate_account_credentials(
    account_data: Dict[str, Any], sfdc_util_ob: su.SFDCUtil
) -> bool:
    if not account_data:
        return False

    sfdc_util_ob.proxies = sfdc_util_ob.build_proxy_info()
    sfdc_util_ob.sslconfig = sfdc_util_ob.get_sslconfig()
    sfdc_util_ob.account_info = account_data

    if account_data.get("auth_type") == "oauth_client_credentials":
        try:
            resp = sfdc_util_ob.get_token()
            if resp.ok:
                return True
        except Exception as e:
            log.log_exception(
                sfdc_util_ob.logger,
                e,
                "Account credentials validation Error",
                msg_before=f"Failed to get oauth token: {e}.\nReason: {traceback.format_exc()}",
            )
        else:
            raise AccountValidationError(resp.text)
    elif account_data.get("auth_type") == "oauth":
        # exiting for oauth auth_type as its account validation is already done in JS.
        return True
    else:
        try:
            resp = sfdc_util_ob.login_sfdc()
        except Exception as e:
            error_msg = (
                f"Some error occurred while validating credentials for salesforce username {account_data['username']}. "
                "Check the log for more details."
            )
            log.log_exception(
                sfdc_util_ob.logger,
                e,
                "Account credentials validation Error",
                msg_before=(
                    f"While validating credentials for salesforce username {account_data['username']}, an error occurred. "
                    f"Check your network connection and try again.\nreason={traceback.format_exc()}"
                ),
            )
            raise AccountValidationError(error_msg)
        else:
            return _process_login_response(resp, account_data, sfdc_util_ob)

    # Should never occur
    raise AccountValidationError(
        "Something went wrong while validating account credentials."
    )


def _process_login_response(
    response, account_data: Dict[str, Any], sfdc_util_ob: su.SFDCUtil
) -> bool:
    if response.status_code == 200:
        sfdc_util_ob.logger.info(
            f"Successfully validated Salesforce account credentials for username {account_data['username']}."
        )
        return True

    content = response.content.decode()
    fault_string, fault_msg = sfdc_util_ob.handle_failed_login(content)
    error_msg = f"Login failed for Salesforce account {account_data['username']} due to {fault_string}."
    log.log_exception(
        sfdc_util_ob.logger,
        Exception(fault_string),
        "Login process response Error",
        msg_before=error_msg,
    )

    raise AccountValidationError(fault_msg)


class GetSessionKey(admin.MConfigHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class AccountValidation(Validator):
    def __init__(self, *args, **kwargs):
        super(AccountValidation, self).__init__(*args, **kwargs)

    def validate(self, value: Any, data: Dict[str, Any]) -> bool:
        if not data:
            return False

        self.sfdc_util_ob = su.SFDCUtil(
            log_file="splunk_ta_salesforce_account_validation",
            session_key=GetSessionKey().session_key,
        )

        try:
            return _validate_account_credentials(data, self.sfdc_util_ob)
        except AccountValidationError as e:
            self.put_msg(str(e), True)
            return False
