"""TA-cisco_catalyst_cybervision_account."""
import logging
import os
import traceback
import splunk.admin as admin

import import_declare_test  # noqa: F401
from TA_cisco_catalyst_cybervision_server_validation import ValidateAccount
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    RestModel,
    SingleModel,
    field,
    validator,
)
from solnlib import conf_manager
from utils import is_true
from consts import CYBER_VISION_CERT_FILE_LOC
import logger_manager

logger = logger_manager.get_logger("cybervision_account_validation")

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "copy_account_name",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=50,
        ),
    ),
    field.RestField(
        'ip_address',
        required=True,
        encrypted=False,
        default=None,
        validator=ValidateAccount()
    ),
    field.RestField(
        'api_token',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
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
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ),
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=4096,
        )
    ),
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=1,
            max_val=65535,
        )
    ),
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=50,
        )
    ),
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_cisco_catalyst_cyber_vision_account',
    model,
    config_name='account'
)


class AccountHandler(AdminExternalHandler):
    """Handle the REST request to configure or remove a CyberVision account."""

    def __init__(self, *args, **kwargs):
        """Initialize the AccountHandler with the given arguments."""
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, confInfo):
        """Remove an existing account if not used by any input."""
        input_conf_file_name = "inputs"
        account_conf_file_name = "ta_cisco_catalyst_cyber_vision_account"
        APP_NAME = import_declare_test.ta_name
        account_stanza_name = self.callerArgs.id
        try:
            account_conf_file = conf_manager.ConfManager(
                self.getSessionKey(),
                APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, account_conf_file_name),
            ).get_conf(account_conf_file_name)
            account_conf_file_stanza = account_conf_file.get(account_stanza_name)

            inputs_conf_file = conf_manager.ConfManager(
                self.getSessionKey(),
                APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, input_conf_file_name),
            ).get_conf(input_conf_file_name)
            inputs_file = inputs_conf_file.get_all(only_current_app=True)
            created_inputs = list(inputs_file.keys())
            input_list = []
            input_type_list = [
                "cisco_catalyst_cybervision_activities",
                "cisco_catalyst_cybervision_components",
                "cisco_catalyst_cybervision_devices",
                "cisco_catalyst_cybervision_events",
                "cisco_catalyst_cybervision_flows",
                "cisco_catalyst_cybervision_vulnerabilities"
            ]

            for _input in created_inputs:
                cisco_cv_input = _input.split('://')
                if cisco_cv_input[0] in input_type_list:
                    configured_account = inputs_file.get(_input).get('cyber_vision_account')
                    if configured_account == account_stanza_name:
                        input_list.append(cisco_cv_input[1])
            if len(input_list) > 0:
                raise admin.ArgValidationException(
                    "Account '{}' can not be deleted because it is linked with the following inputs= {}".format(
                        account_stanza_name, input_list
                    )
                )
            if is_true(account_conf_file_stanza.get("use_ca_cert", False)):
                cert_file_name = account_conf_file_stanza.get("copy_account_name")
                cert_file_loc = CYBER_VISION_CERT_FILE_LOC.format(cert_name=cert_file_name)
                if os.path.exists(cert_file_loc):
                    os.remove(cert_file_loc)
                    logger.info(
                        "account_name={} | message=CA_cert_deleted_successfully | CA cert deleted successfully "
                        "for the Account: {}".format(account_stanza_name, account_stanza_name)
                    )
            super(AccountHandler, self).handleRemove(confInfo)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise admin.ArgValidationException(e)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AccountHandler,
    )
