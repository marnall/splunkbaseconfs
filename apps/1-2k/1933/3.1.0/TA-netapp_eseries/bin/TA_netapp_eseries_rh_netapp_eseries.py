
import ta_netapp_eseries_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
import os
import re
import splunk.admin as admin
import splunk.entity as entity
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from netapp_connect import NetAppConnection
import netapp_eseries_utility as utility
util.remove_http_proxy_env_vars()
from TA_netapp_eseries_log_manager import setup_logging

logger = setup_logging("ta_netapp_eseries_netapp_eseries")


class CustomConfigMigrationHandler(ConfigMigrationHandler):
    
    def input_validation(self):
        interval = float(self.payload.get('interval', None))
        system_id = self.payload.get('system_id')
        my_app = os.path.abspath(__file__).split('/')[-3] if '/' in os.path.abspath(__file__) else os.path.abspath(__file__).split('\\')[-3]
        global_account_name = self.payload.get('global_account')

        if interval <= 0:
            logger.error("NetApp ESeries Error: Interval must be a positive integer.")
            raise admin.ArgValidationException("Interval must be a positive integer.")

        if not re.match(r'^[-a-zA-Z0-9]+$', system_id):
            logger.error("NetApp ESeries Error: Please enter valid System ID.")
            raise admin.ArgValidationException("Please enter valid System ID")

        account_data = utility.getAccountData(global_account_name, my_app)

        if 'verify_ssl' not in account_data:
            verify_ssl_certificate = utility.get_verify_ssl()
        else:
            verify_ssl_certificate = False if account_data["verify_ssl"] in ["0", "False", "F", "false", "f"] else True

        session_key = self.getSessionKey()
        entities = entity.getEntities(['admin', 'passwords'], namespace=my_app, owner='nobody', sessionKey=session_key,
                                    search=my_app)
        proxies = utility.getProxySettings(my_app, entities)
        password = utility.getPassword(entities, global_account_name)

        netapp_connection = NetAppConnection(account_data["web_proxy"], account_data["username"], password, proxies,
                                            verify_ssl_certificate)
        response = netapp_connection.checkSystemId()

        check_system_id = False
        for data in response:
            if system_id == data.get('id'):
                check_system_id = True
                break

        if not check_system_id:
            logger.error("NetApp ESeries Error: Given System ID does not exist.")
            raise admin.ArgValidationException("Given System ID does not exist.")

    def handleCreate(self, confInfo):
        """Handle creation of account in config file."""
        self.input_validation()
        super(CustomConfigMigrationHandler, self).handleCreate(confInfo)

    def handleEdit(self, confInfo):
        """Handles the edit operation."""
        if 'disabled' not in self.payload:
            self.input_validation()
        super(CustomConfigMigrationHandler, self).handleEdit(confInfo)


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=60,
        validator=validator.Pattern(
            regex=r"""^\[1-9]\d*$|^\d*$""", 
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
        'system_id',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
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
    'netapp_eseries',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )
