"""TA-cisco_catalyst_ise_account."""

import logging
import os
import traceback
import splunk.admin as admin

import import_declare_test  # noqa: F401
from ise.TA_cisco_catalyst_ise_server_validation import (
    ValidateAccount, ValidateReportAccount
)
import ise.pxgrid_api_helper as pxapi
import utils
import cisco_catalyst_exceptions as cce
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    RestModel,
    SingleModel,
    field,
    validator,
)
from solnlib import conf_manager

from consts import (
    ISE_CERT_FILE_LOC,
    ISE_CLIENT_CERT_FILE_LOC,
)
import logger_manager

logger = logger_manager.get_logger("ise_account_validation")

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'account_type',
        required=False,
        encrypted=False,
        default="administrative",
        validator=None
    ),
    field.RestField(
        "copy_account_name",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=50,
        ),
    ),
    field.RestField(
        "hostname",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        ),
    ),
    field.RestField(
        "username",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        ),
    ),
    field.RestField(
        "password",
        required=False,
        encrypted=True,
        default=None,
        validator=ValidateAccount(),
    ),
    field.RestField(
        "pxgrid_host",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "pxgrid_client_username",
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        "pxgrid_client_password",
        required=False,
        encrypted=True,
        default=None,
        validator=None,
    ),
    field.RestField(
        "pxgrid_cert_auth",
        required=False,
        encrypted=False,
        default=False,
        validator=None,
    ),
    field.RestField(
        "client_cert",
        required=False,
        encrypted=False,
        default="",
        validator=None,
    ),
    field.RestField(
        "client_key",
        required=False,
        encrypted=False,
        default="",
        validator=None,
    ),
    field.RestField(
        "use_ca_cert",
        required=False,
        encrypted=False,
        default=False,
        validator=None,
    ),
    field.RestField(
        "custom_certificate",
        required=False,
        encrypted=False,
        default="",
        validator=None,
    ),
    field.RestField(
        "enable_proxy",
        required=False,
        encrypted=False,
        default=False,
        validator=None,
    ),
    field.RestField(
        "proxy_type", required=False, encrypted=False, default="http", validator=None
    ),
    field.RestField(
        "proxy_url",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=4096,
        ),
    ),
    field.RestField(
        "proxy_port",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=1,
            max_val=65535,
        ),
    ),
    field.RestField(
        "proxy_username",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=50,
        ),
    ),
    field.RestField(
        "proxy_password",
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        'ise_ssh_port',
        required=False,
        encrypted=False,
        default='22',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'sftp_repo_ip',
        required=False,
        encrypted=False,
        default=None,
        validator=ValidateReportAccount(),
    ), 
    field.RestField(
        'sftp_repo_user',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'sftp_repo_pw',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'sftp_repo_port',
        required=False,
        encrypted=False,
        default='22',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
]
model = RestModel(fields, name=None)


endpoint = SingleModel("ta_cisco_catalyst_ise_account", model, config_name="account")


class AccountHandler(AdminExternalHandler):
    """Handle the REST request to configure or remove a ISE account."""

    def __init__(self, *args, **kwargs):
        """Initialize the AccountHandler with the given arguments."""
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, confInfo):
        """Remove an existing account if not used by any input."""
        input_conf_file_name = "inputs"
        account_conf_file_name = "ta_cisco_catalyst_ise_account"
        APP_NAME = import_declare_test.ta_name
        account_stanza_name = self.callerArgs.id
        try:
            account_conf_file = conf_manager.ConfManager(
                self.getSessionKey(),
                APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
                    APP_NAME, account_conf_file_name
                ),
            ).get_conf(account_conf_file_name)
            account_conf_file_stanza = account_conf_file.get(account_stanza_name)

            inputs_conf_file = conf_manager.ConfManager(
                self.getSessionKey(),
                APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(
                    APP_NAME, input_conf_file_name
                ),
            ).get_conf(input_conf_file_name)
            inputs_file = inputs_conf_file.get_all(only_current_app=True)
            created_inputs = list(inputs_file.keys())
            input_list = []

            input_type_list = ["cisco_catalyst_ise_administrative_input", "cisco_catalyst_ise_analytics_reports"]

            account_type = account_conf_file_stanza.get("account_type", "administrative")
            for _input in created_inputs:
                cisco_ise_input = _input.split("://")
                if cisco_ise_input[0] in input_type_list:
                    configured_account = inputs_file.get(_input).get("ise_account")
                    if configured_account == account_stanza_name:
                        if cisco_ise_input[0] == "cisco_catalyst_ise_administrative_input" and account_type == "administrative":
                            input_list.append(cisco_ise_input[1])
                        elif account_type == "reports":
                            input_list.append(cisco_ise_input[1])
            if len(input_list) > 0:
                raise admin.ArgValidationException(
                    "Account '{}' can not be deleted because it is linked with the following inputs= {}".format(
                        account_stanza_name, input_list
                    )
                )
            pxgrid_host = account_conf_file_stanza.get("pxgrid_host")
            pxgrid_client_username = account_conf_file_stanza.get("pxgrid_client_username")
            if pxgrid_host and pxgrid_client_username:
                username = account_conf_file_stanza.get("username")
                password = account_conf_file_stanza.get("password")
                headers = utils.make_headers(username, password)
                config = utils.Config(self.getSessionKey(), account_conf_file_stanza, logger)
                verify_ssl = config.get_verify_ssl_cert()
                proxy_settings = config.get_proxy_settings()
                pxgrid = pxapi.CiscopxGrid(
                    pxgrid_client_username=pxgrid_client_username,
                    logger=logger,
                    hostname=account_conf_file_stanza.get("hostname"),
                    headers=headers,
                    verify_ssl=verify_ssl,
                    proxy=proxy_settings,
                )
                delete_username_response = pxgrid.delete_username()
                if delete_username_response.status_code in (200, 201, 204, 404):
                    logger.info(
                        "account_name={} | message=pxgrid_client_deleted_successfully | pxGrid client {} deleted "
                        "successfully.".format(account_stanza_name, pxgrid_client_username)
                    )
                else:
                    err_log = (
                        "Error occurred while deleting pxGrid client {}."
                        " | Error={}"
                    )
                    raise cce.InvalidStatusCodeError(
                        err_log.format(pxgrid_client_username, delete_username_response.text)
                    )
            cert_file_name = account_conf_file_stanza.get("copy_account_name")
            cert_file_loc = ISE_CERT_FILE_LOC.format(cert_name=cert_file_name)
            pxgrid_cert_file_loc = ISE_CLIENT_CERT_FILE_LOC.format(cert_name=cert_file_name)
            if os.path.exists(cert_file_loc):
                os.remove(cert_file_loc)
                logger.info(
                    "account_name={} | message=CA_cert_deleted_successfully | CA cert deleted successfully "
                    "for the Account: {}".format(
                        account_stanza_name, account_stanza_name
                    )
                )
            if os.path.exists(pxgrid_cert_file_loc):
                os.remove(pxgrid_cert_file_loc)
                logger.info(
                    "account_name={} | message=PxGrid_cert_deleted_successfully | PxGrid cert deleted successfully "
                    "for the Account: {}".format(
                        account_stanza_name, account_stanza_name
                    )
                )
            super(AccountHandler, self).handleRemove(confInfo)
        except cce.InvalidStatusCodeError as e:
            logger.error(e)
            raise admin.ArgValidationException(e)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise admin.ArgValidationException(e)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AccountHandler,
    )
