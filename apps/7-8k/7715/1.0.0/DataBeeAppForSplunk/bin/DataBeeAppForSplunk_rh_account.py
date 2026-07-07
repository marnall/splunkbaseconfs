
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from databee_helpers.validators import HTTPCollectorValidator, AlertActionValidator
from databee_helpers.conf_helper import get_conf_file, create_service, update_alert_action
from databee_helpers.logger_manager import setup_logging
import logging
import splunk.admin as admin

util.remove_http_proxy_env_vars()


class DataBeeAccountHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, confInfo):
        try:
            acc_name = self.callerArgs.id
            logger = setup_logging('ta_databee_account_deletion', account_name=acc_name)
            logger.info("Account Deletion started.")
            
            parameters = get_conf_file(
                file="databeeappforsplunk_account",
                session_key=self.getSessionKey(),
                stanza=acc_name
            )
            enabled_saved_searches = parameters.get("alert_actions")
            list_to_disable_saved_searches = enabled_saved_searches.split(",")
            
            service = create_service()
            update_alert_action(self.getSessionKey(), acc_name, logger, service, list_to_disable_saved_searches, 0)
            
            super(DataBeeAccountHandler, self).handleRemove(confInfo)
            logger.info("Account Deleted Successfully.")

        except Exception as e:
            logger.error("message=account_deletion_error | "
                         "DataBee account deletion Error occured \"{}\"".format(traceback.format_exc()))
            raise admin.ArgValidationException(e)


fields = [
    field.RestField(
        'copy_account_name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=50,
        ),
    ),
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=HTTPCollectorValidator(),
    ),  
    field.RestField(
        'endpoint_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ),  
    field.RestField(
        'tenant_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ),  
    field.RestField(
        'datasource_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=8192, 
            min_len=1, 
        )
    ),  
    field.RestField(
        'alert_actions',
        required=True,
        encrypted=False,
        default=None,
        validator=AlertActionValidator()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'databeeappforsplunk_account',
    model,
    config_name='account'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=DataBeeAccountHandler,
    )
