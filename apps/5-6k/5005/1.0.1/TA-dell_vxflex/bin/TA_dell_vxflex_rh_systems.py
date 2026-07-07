
import ta_dell_vxflex_declare
import vxflex_utilities
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)

from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler.endpoint.validator import Validator
from solnlib import conf_manager
from vxflex_account import VxFlexAccountValidator
from vxflex_utilities import get_accounts
from splunktaucclib.rest_handler.error import RestError

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'endpoint',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"^(?!http|https).*",
        )
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
        validator=VxFlexAccountValidator()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_dell_vxflex_systems',
    model,
)

class CustomInputsHandler(ConfigMigrationHandler):

    def handleCreate(self, confInfo):
        logger = vxflex_utilities.get_logger(self.getSessionKey(), 'ta_dell_vxflex_account_validation', "validator")

        if not self.check_duplicates(logger):
            raise RestError(409, "This system is already configured. Try configuring with different username.")
        
        super(CustomInputsHandler,self).handleCreate(confInfo)
        try:
            stanzas = vxflex_utilities.read_conf_file(self.getSessionKey(), vxflex_utilities.VXFLEX_ENDPOINTS)
            vxflex_utilities.create_vxflex_input(self.callerArgs.id, stanzas, self.getSessionKey(), logger)
        except Exception:
            logger.exception("Error while creating modular input stanza.")
    
    def handleEdit(self, confInfo):
        logger = vxflex_utilities.get_logger(self.getSessionKey(), 'ta_dell_vxflex_account_validation', "validator")
        if not self.check_duplicates(logger):
            raise RestError(409, "This system is already configured. Try configuring with different username.")
        else:
            super(CustomInputsHandler,self).handleEdit(confInfo)

    def check_duplicates(self, logger):
        try:
            existing_accounts = None
            try:
                existing_accounts = get_accounts(self.getSessionKey())
            except:
                logger.info("Unable to fetch systems or systems files conf file does not exists, allowing system to be added.")
                return True

            for key, ac in existing_accounts.items():
                if ac['endpoint'] == self.payload.get('endpoint') and ac['username'] == self.payload.get('username') and key != str(self.callerArgs.id):
                    logger.debug("Key={}, Existing same system name={}, Endpoint={}, Username={}".format(self.callerArgs.id, key, self.payload.get('endpoint'), self.payload.get('username')))
                    return False
            return True
        except Exception as exc:
            logger.exception(str(exc))
            return False


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomInputsHandler,
    )
