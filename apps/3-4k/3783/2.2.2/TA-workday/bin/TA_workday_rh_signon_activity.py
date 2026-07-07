
import ta_workday_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
import sys, json
import re

import splunk.rest as rest
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

from splunktaucclib.rest_handler.admin_external import AdminExternalHandler


util.remove_http_proxy_env_vars()

app_name = ta_workday_declare.ta_name

fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""", 
        )
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1, 
            max_len=80, 
        )
    ), 
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'report_url',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'from_moment',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\d{4}-\d{2}-\d{2}T\d{2}\:\d{2}\:\d{2}Z""", 
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
    'signon_activity',
    model,
)

class CustomConfigMigrationHandlerUserActivity(AdminExternalHandler):

    '''
    Manage the Rest Handler for Inputs
    '''

    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def checkpointer_delete(self, session_key, input_name, input_type ):
        # response_status, response_content = rest.simpleRequest("/servicesNS/nobody/" + str(app_name) + "/storage/collections/data/" + str(app_name.replace(
            # '-', '_')) + "_checkpointer/" + str(self.callerArgs.id), sessionKey=session_key, method='DELETE', getargs={"output_mode": "json"}, raiseAllErrors=True)
        try:
            APP_NAME = str(app_name)
            CHECKPOINTER = str(app_name.replace('-','_'))+"_checkpointer"
            checkpoint_name = str(self.callerArgs.id)
            rest_url = "/servicesNS/nobody/{}/storage/collections/data/{}/{}".format(
                APP_NAME, CHECKPOINTER, checkpoint_name
            )
    
            _, _ = rest.simpleRequest(
                rest_url,
                sessionKey=session_key,
                method="DELETE",
                getargs={"output_mode": "json"},
                raiseAllErrors=True,
            )

            logger.info("Deleted checkpoint for input : {}".format(input_name))

        except Exception as e:
            logger.error("Error deleting checkpoint : {}".format(e))
            sys.exit(1)

    def handleRemove(self, confInfo):
        session_key = self.getSessionKey()
        input_name = self.callerArgs.id
        input_type = 'signon_activity' #self.handler.get_endpoint().input_type
        AdminExternalHandler.handleRemove(self, confInfo)
        try:
            self.checkpointer_delete(session_key, input_name, input_type)
        except:
            pass
        

    def checkpointer_change(self, session_key, input_name, input_type ):
        args = {}
        pattern = re.compile("^\d{4}-\d{2}-\d{2}T\d{2}\:\d{2}\:\d{2}Z")
        
        if self.payload.get('from_moment') and pattern.match(self.payload.get('from_moment')):
            
            args['state'] = '\"'+str(self.payload.get('from_moment'))+'\"'
            APP_NAME = str(app_name)
            CHECKPOINTER = str(app_name.replace('-','_'))+"_checkpointer"
            checkpoint_name = str(self.callerArgs.id)
            rest_url = "/servicesNS/nobody/{}/storage/collections/data/{}/{}".format(
                    APP_NAME, CHECKPOINTER, checkpoint_name
                )
            try:
                rest.simpleRequest(
                    rest_url,
                    sessionKey=self.getSessionKey(),
                    jsonargs=json.dumps(args),
                    method="POST",
                    raiseAllErrors=True,
                )        
            except Exception as exc:
                logger.error("Changed checkpoint failed. Reason : "+str(exc))

    def handleEdit(self, confInfo):
        session_key = self.getSessionKey()
        input_name = self.callerArgs.id
        input_type = 'signon_activity' #self.handler.get_endpoint().input_type
        self.checkpointer_change(session_key, input_name, input_type)
        AdminExternalHandler.handleEdit(self, confInfo)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandlerUserActivity,
    )
