
import logging
import os
import traceback
import splunk.admin as admin


import import_declare_test
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    RestModel,
    SingleModel,
    field,
    validator,
)
from solnlib import conf_manager
from TA_cisco_catalyst_dnac_account_validation import ValidateCatalystCenterHost
from utils import is_true
from consts import CATALYSTC_CERT_FILE_LOC
import logger_manager
logger = logger_manager.get_logger("catalyst_center_account_validation")
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
        'username',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=200, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
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
        "cisco_dna_center_host",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=8192, 
                min_len=0, 
            ), 
            validator.Pattern(
                regex=r"""^https:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$""", 
            ),
            ValidateCatalystCenterHost(),
        )
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_cisco_catalyst_account',
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
        account_conf_file_name = "ta_cisco_catalyst_account"
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
                "cisco_catalyst_dnac_issue",
                "cisco_catalyst_dnac_clienthealth",
                "cisco_catalyst_dnac_devicehealth",
                "cisco_catalyst_dnac_compliance",
                "cisco_catalyst_dnac_networkhealth",
                "cisco_catalyst_dnac_securityadvisory",
                "cisco_catalyst_dnac_client",
                "cisco_catalyst_dnac_audit_logs",
                "cisco_catalyst_dnac_site_topology",
                "cisco_catalyst_center_reports"
            ]

            for _input in created_inputs:
                cisco_cv_input = _input.split('://')
                if cisco_cv_input[0] in input_type_list:
                    configured_account = inputs_file.get(_input).get('cisco_dna_center_account')
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
                cert_file_loc = CATALYSTC_CERT_FILE_LOC.format(cert_name=cert_file_name)
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
