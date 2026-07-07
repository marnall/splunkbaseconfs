
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import splunk.admin as admin
from silent_push_helpers.validators import AccountValidator, ThreatCheckValidator
from silent_push_helpers.conf_helper import get_conf_file
from silent_push_helpers.logger_manager import setup_logging
import logging
import traceback

util.remove_http_proxy_env_vars()


class SilentPushAccountHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, confInfo):
        try:
            acc_name = self.callerArgs.id
            logger = setup_logging('ta_silent_push_account_deletion', account_name=acc_name)
            logger.info("message=account_deletion_start | Account Deletion started.")
            conf_file = get_conf_file(
                file="inputs",
                session_key=self.getSessionKey(),
            )
            inputs_file = conf_file.get_all(only_current_app=True)
            created_inputs = list(inputs_file.keys())
            
            input_list = []
            input_type_list = ["silent_push_indicator"]

            for _input in created_inputs:
                silent_push_input = _input.split('://')
                if silent_push_input[0] in input_type_list:
                    configured_account = inputs_file.get(_input).get('global_account')
                    if configured_account == acc_name:
                        input_list.append(silent_push_input[1])
            if len(input_list) > 0:
                raise admin.ArgValidationException(
                    "Account \"{}\" can not be deleted because it is in use by the following inputs: {}".format(
                        acc_name, input_list
                    )
                )
            else:
                super(SilentPushAccountHandler, self).handleRemove(confInfo)
                logger.info("message=account_deletion_success | Account Deleted Successfully.")

        except Exception as e:
            logger.error("message=account_deletion_error | "
                         "Silent Push account deletion Error occured \"{}\"".format(traceback.format_exc()))
            raise admin.ArgValidationException(e)


fields = [
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=AccountValidator()
    ),
    field.RestField(
        'add_threat_check_api',
        required=False,
        default=False,
        validator=None
    ),
    field.RestField(
        'threat_check_api_key',
        required=False,
        encrypted=True,
        default=None,
        validator=ThreatCheckValidator()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'silentpushappforsplunk_account',
    model,
    config_name='account'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=SilentPushAccountHandler,
    )
