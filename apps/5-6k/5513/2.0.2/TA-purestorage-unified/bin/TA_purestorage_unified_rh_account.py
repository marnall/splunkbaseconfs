import ta_purestorage_unified_declare  # noqa:   401
from purestorage_server_validation import ValidateAccount
from splunk import admin
from solnlib import conf_manager
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from logger_manager import setup_logging

util.remove_http_proxy_env_vars()
TA_NAME = TA_NAME = ta_purestorage_unified_declare.ta_name
logger = setup_logging("purestorage_unified_ta_account_handler")


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


class AccountHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server.

    :param ConfigMigrationHandler: inhereting ConfigMigrationHandler
    """

    def get_inputs(self, session_key, conf_file, stanza=None):
        """
        Get conf file content with conf_manager.

        :param session_key: Splunk session key
        :param conf_file: conf file name
        :param stanza: If stanza name is present then return only that stanza,
                        otherwise return all stanza
        """
        conf_file = conf_manager.ConfManager(
            session_key,
            TA_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(TA_NAME, conf_file),
        ).get_conf(conf_file)

        if stanza:
            return conf_file.get(stanza)
        return conf_file.get_all()

    def handleRemove(self, confInfo):
        """Handle the delete operation."""
        session_key = GetSessionKey().session_key
        inputs_file = self.get_inputs(session_key, "inputs")
        created_inputs = list(inputs_file.keys())
        input_list = []
        input_type = "purestorage_unified_input"
        for _input in created_inputs:
            psinput = _input.split('://')
            if psinput[0] == input_type:
                configured_account = inputs_file.get(_input).get('global_account')
                if configured_account == self.callerArgs.id:
                    input_list.append(psinput[1])
        if len(input_list) > 0:
            raise admin.ArgValidationException(
                "\"{}\" cannot be deleted because it is in use".format(self.callerArgs.id))
        else:
            super(ConfigMigrationHandler, self).handleRemove(confInfo)


fields = [
    field.RestField('server_address',
                    required=True,
                    encrypted=False,
                    default=None,
                    validator=ValidateAccount()),
    field.RestField('account_type',
                    required=True,
                    encrypted=False,
                    default='flash_blade_account',
                    validator=validator.String(
                        min_len=1,
                        max_len=8192,
                    )),
    field.RestField('api_token',
                    required=True,
                    encrypted=True,
                    default=None,
                    validator=validator.String(
                        min_len=1,
                        max_len=8192,
                    ))
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_purestorage_unified_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AccountHandler,
    )
