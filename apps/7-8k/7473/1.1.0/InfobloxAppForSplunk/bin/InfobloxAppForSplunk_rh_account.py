
import import_declare_test

import traceback
import logging
import splunk.admin as admin

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from solnlib import conf_manager
from infoblox_helpers.constants import APP_NAME
from infoblox_helpers.logger_manager import setup_logging
from infoblox_helpers.validators import AccountValidator

logger = setup_logging("ta_infoblox_rh_account")
util.remove_http_proxy_env_vars()

class CustomAccountHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, conf_info):
        conf_file = "inputs"
        try:
            conf_file = conf_manager.ConfManager(
                self.getSessionKey(),
                APP_NAME,
                realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, conf_file),
            ).get_conf(conf_file)
            inputs_file = conf_file.get_all(only_current_app=True)
            created_inputs = list(inputs_file.keys())

        except Exception as e:
            logger.error("message=account_deletion_error | "
                         "Infoblox account deletion: Error occured while getting input details."
                         " Error_message=\"{}\"".format(traceback.format_exc()))
            raise admin.ArgValidationException("Error occured while getting input details. Error=\"{}\"".format(str(e)))
        else:
            input_list = []
            input_type_list = ["infoblox_insights", "infoblox_threat_intelligence"]

            for _input in created_inputs:
                infoblox_input = _input.split('://')
                if infoblox_input[0] in input_type_list:
                    configured_account = inputs_file.get(_input).get('global_account')
                    if configured_account == self.callerArgs.id:
                        input_list.append(infoblox_input[1])
            if len(input_list) > 0:
                logger.error("message=account_deletion_error |"
                             "Infoblox account deletion: Account \"{}\" can not be deleted because "
                             "it is linked with the following inputs: [\"{}\"]".format(self.callerArgs.id,"\", \"".join(input_list)))
                raise admin.ArgValidationException(
                    "Account \"{}\" can not be deleted because it is linked with the following inputs=[\"{}\"]"
                    .format(self.callerArgs.id,"\", \"".join(input_list)))
            else:
                super(CustomAccountHandler, self).handleRemove(conf_info)


fields = [
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=AccountValidator()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'infobloxappforsplunk_account',
    model,
    config_name='account'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CustomAccountHandler,
    )
