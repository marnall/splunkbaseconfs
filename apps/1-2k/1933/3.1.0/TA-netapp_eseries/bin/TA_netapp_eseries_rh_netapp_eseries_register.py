
import ta_netapp_eseries_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
import os
import splunk.entity as entity
import splunk.admin as admin
from netapp_connect import NetAppConnection
import netapp_eseries_utility as utility
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
util.remove_http_proxy_env_vars()
from TA_netapp_eseries_log_manager import setup_logging

logger = setup_logging("ta_netapp_eseries_netapp_eseries_register")


class CustomConfigMigrationHandler(ConfigMigrationHandler):
    
    def input_validation(self):
        try:
            my_app =  os.path.abspath(__file__).split('/')[-3] if '/' in os.path.abspath(__file__) else os.path.abspath(__file__).split('\\')[-3]
            interval = float(self.payload.get('interval',None))
            name = self.callerArgs.id
            interval = float(interval)
            global_account = self.payload.get('global_account')
            ip1 = self.payload.get('ip1')
            ip2 = self.payload.get('ip2')

            if interval <= 0:
                logger.error("NetApp ESeries Error: Interval must be a positive integer.")
                msg ="Interval must be a positive integer."
                raise admin.ArgValidationException(msg)

            if not utility.validateIp(ip1) or not utility.validateIp(ip2):
                logger.error("NetApp ESeries Error: Invalid controller IP addresses.")
                msg = "Invalid controller IP addresses."
                raise admin.ArgValidationException(msg)

            account_dict = utility.getAccountData(global_account, my_app)

            if 'verify_ssl' not in account_dict:
                verify_ssl = utility.get_verify_ssl()
            else:
                verify_ssl = False if account_dict["verify_ssl"] in ["0", "False", "F", "false", "f"] else True

            session_key = self.getSessionKey()
            entities = entity.getEntities(['admin', 'passwords'], namespace=my_app, owner='nobody', sessionKey=session_key,
                                        search=my_app)
            proxy_settings = utility.getProxySettings(my_app, entities)
            password = utility.getPassword(entities, global_account)

            netapp_connection = NetAppConnection(account_dict["web_proxy"], account_dict["username"], password, proxy_settings,
                                                verify_ssl)

            register_password = utility.getPassword(entities, name)
            try:
                array_id = utility.registerArray(ip1, ip2, register_password, netapp_connection)
            except Exception as e:
                logger.error("NetApp Eseries Register Error: {}".format(e))
                raise admin.ArgValidationException(e)
            if not array_id:
                logger.error("NetApp ESeries Error: Please enter correct controller IPs and password.")
                msg = "Please enter correct controller IPs and password."
                raise admin.ArgValidationException(msg)
            logger.info("Eseries Register and Monitor Input Validated.")
        except Exception as e:
            logger.error("NetApp Eseries Register Error: {}".format(e))
            raise admin.ArgValidationException(
                "Unexpected error occured while saving the account, please take a look at\
                ta_netapp_eseries_netapp_eseries_register.log for more details."
            )


    def handleCreate(self, confInfo):
        """Handle creation of account in config file."""
        self.input_validation()
        super(CustomConfigMigrationHandler, self).handleCreate(confInfo)

    def handleEdit(self, confInfo):
        """Handles the edit operation. """
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
        'ip1',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=7, 
            max_len=39, 
        )
    ), 
    field.RestField(
        'ip2',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=7, 
            max_len=39, 
        )
    ), 
    field.RestField(
        'password',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
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
    'netapp_eseries_register',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )
