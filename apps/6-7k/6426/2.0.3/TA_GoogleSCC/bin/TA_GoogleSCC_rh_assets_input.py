
import import_declare_test
import traceback
from import_declare_test import ta_name
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
import splunk.rest as rest
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging
from TA_GoogleSCC_logger_manager import setup_logging
from TA_GoogleSCC_input_validation import CredsValidator

util.remove_http_proxy_env_vars()
logger = setup_logging("ta_googlescc_rh_assets_log")

class CustomHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        """
        This class handles the parameters in the configuration page
        """
        AdminExternalHandler.__init__(self, *args, **kwargs)
    
    def handleRemove(self, conf_info):
        """
        :param conf_info: The dictionary containing configurable parameters.
        :return: None
        """
        session_key = self.getSessionKey()
        try:
            response_status, response_content = rest.simpleRequest(
                "/servicesNS/nobody/" + str(ta_name) +"/storage/collections/data/" + "assets_input_" + str(
                    self.callerArgs.id),
                sessionKey=session_key, method='DELETE', getargs={"output_mode": "json"}, raiseAllErrors=True)
        except Exception:
            logger.error("message=rest_call_error | Error occured.\n{}".format(traceback.format_exc()))
        finally:
            super(CustomHandler, self).handleRemove(conf_info)
        
fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='300',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^\-[1-9]\d*$|^\d*$""", 
            ), 
            validator.Number(
                max_val=900, 
                min_val=300, 
            )
        )
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            max_len=80, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'google_scc_account',
        required=True,
        encrypted=False,
        default=None,
        validator=CredsValidator()
    ), 
    field.RestField(
        'assets_subscription_id',
        required=True,
        encrypted=False,
        default='',
        validator=validator.Pattern(
            regex=r"""^projects/[^/]+/subscriptions/[^/]+$"""
        )
    ), 
    field.RestField(
        'maximum_fetching',
        required=True,
        encrypted=False,
        default='500',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^\-[1-9]\d*$|^\d*$""", 
            ), 
            validator.Number(
                max_val=5000, 
                min_val=500, 
            )
        )
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'assets_input',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CustomHandler,
    )
