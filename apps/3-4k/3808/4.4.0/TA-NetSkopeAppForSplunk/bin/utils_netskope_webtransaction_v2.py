"""Utilities related to netskope modular input."""
import ta_netskopeappforsplunk_declare  # noqa: F401

import sys
import os
import json
import netskope_utils

from netskope_utils import GetSessionKey, APP_NAME, read_conf_file

from splunktaucclib.rest_handler.endpoint import DataInputModel
from splunktaucclib.rest_handler.error import RestError

from solnlib.credentials import CredentialManager

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            __file__,
            "..",
            "ta_netskopeappforsplunk",
            "netskope_iterator_sdk",
        )
    ),
)

from netskope_api.iterator.const import Const
from netskope_api.token_management.netskope_management import NetskopeTokenManagement

BAD_REQUEST_STATUS_CODE = 400
NETSKOPE_ACCOUNT_CONF = "ta_netskopeappforsplunk_account"


def get_v2_clear_creds(session_key, global_account):
    """
    Get unencrypted creds from passwords.conf.

    :return: Token and Service Account (json) in clear text
    """
    manager = CredentialManager(
        session_key,
        app=APP_NAME,
        realm="__REST_CREDENTIAL__#{0}#{1}".format(APP_NAME, "configs/conf-ta_netskopeappforsplunk_account"),
    )

    clear_creds = None

    try:
        clear_creds = json.loads(manager.get_password(global_account))
    except Exception as e:
        raise Exception(e)

    return clear_creds


class NetskopeWebTransactionV2Model(DataInputModel):
    """NetskopeModel validator."""

    def validate(self, name, data, existing=None):
        """Validate Input parameters."""
        interval = parallel_ingestion_pipeline = None
        subscription_key = subscription_path = None
        session_key = GetSessionKey().session_key

        # Get the existing data if any for hidden fields
        conf_file_stanzas = read_conf_file(session_key, "inputs")
        for input_stanza in conf_file_stanzas:
            if "netskope_webtransactions_v2://" in input_stanza and input_stanza.split("://")[-1] == name:
                interval = conf_file_stanzas[input_stanza].get("interval")
                parallel_ingestion_pipeline = conf_file_stanzas[input_stanza].get("parallel_ingestion_pipeline")
                subscription_key = conf_file_stanzas[input_stanza].get("subscription_key")
                subscription_path = conf_file_stanzas[input_stanza].get("subscription_path")

        # Add hidden fields to avoid insertion error
        data['interval'] = '0' if interval is None else interval
        data['parallel_ingestion_pipeline'] = '' if parallel_ingestion_pipeline is None else parallel_ingestion_pipeline
        data['subscription_key'] = '' if subscription_key is None else subscription_key
        data['subscription_path'] = '' if subscription_path is None else subscription_path

        account_name = data["global_account"]
        account = get_v2_clear_creds(session_key, account_name)
        account_config = netskope_utils.read_conf_file(session_key, NETSKOPE_ACCOUNT_CONF, stanza=account_name)
        hostname = account_config.get("hostname")
        token_v2 = account.get("token_v2")
        if not token_v2:
            raise RestError(
                BAD_REQUEST_STATUS_CODE,
                'Please configure the "Netskope Account" which is configured with V2 token.'
            )

        params = {
            Const.NSKP_TOKEN: token_v2,
            Const.NSKP_TENANT_HOSTNAME: hostname,
            Const.NSKP_PROXIES: netskope_utils.create_requests_proxy_dict(session_key=session_key),
            Const.NSKP_USER_AGENT: netskope_utils.get_user_agent(hostname, session_key=session_key, is_webtx=True)
        }

        try:
            token_management = NetskopeTokenManagement(params)
            response = token_management.get()

            if not ("subscription" in response and "subscription-key" in response):
                status_code = int(response.get("status", 400))
                # In case of status=449, we will allow configuration of input.
                # Subscription-Key and Subscription path will be regenerated during data collection.
                if status_code != 449:
                    raise RestError(
                        status_code,
                        "Not able to get Subscription Key and Path: {}".format(response.get("error_msg", response))
                    )
            else:
                data["subscription_key"] = response["subscription-key"]
                data["subscription_path"] = response["subscription"]
        except Exception as ex:
            raise RestError(BAD_REQUEST_STATUS_CODE, "Error occured while validating Token V2 parameter: {}".format(ex))

        enable_custom_spool_path = data.get("enable_custom_spool_path")
        enable_custom_spool_path = 0 if enable_custom_spool_path is None else int(enable_custom_spool_path)
        if enable_custom_spool_path:
            custom_path = data.get("custom_spool_path", None)
            if custom_path is None:
                raise RestError(
                    BAD_REQUEST_STATUS_CODE,
                    "Custom Path is required if 'Enable Custom Webtxn Path' is enabled."
                )
            if not os.path.exists(custom_path):
                raise RestError(
                    BAD_REQUEST_STATUS_CODE,
                    "Provided 'Custom Path' is either not valid or does not exist. Please enter a valid 'Custom Path'."
                )
            try:
                file_path = os.path.join(custom_path, "webtx_test_file.txt")
                with open(file_path, "w") as f:
                    f.write("Custom path is valid.")
                if os.path.exists(file_path):
                    os.remove(file_path)
                else:
                    raise RestError(
                        BAD_REQUEST_STATUS_CODE,
                        'Write access is not available for the given path: {}'.format(custom_path)
                    )
            except Exception as ex:
                raise RestError(BAD_REQUEST_STATUS_CODE, "Error occured while validating Custom Path: {}".format(ex))

        super(NetskopeWebTransactionV2Model, self).validate(name, data, existing)
