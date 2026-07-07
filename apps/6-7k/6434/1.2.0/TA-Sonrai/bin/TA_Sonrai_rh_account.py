
import json
import ta_sonrai_declare
import tempfile

from datetime import datetime
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
import common.utility as utility
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from ta_sonrai_account_validation import ValidateSonraiCreds
from splunktaucclib.rest_handler.error import RestError
from splunk import rest

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'organization_id',
        required=True,
        encrypted=False,
        default=None,
        validator=ValidateSonraiCreds()
    ), 
    field.RestField(
        'sonrai_token',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ),
    field.RestField(
        "verify_certs",
        default=True,
        encrypted=False
    ),
    field.RestField(
        "sonrai_host",
        required=True,
        encrypted=False,
        default="app.sonraisecurity.com",
        validator=validator.Pattern(
            regex=r"""[a-z0-9.\\-]+[.][a-z]{2,4}""",
        )
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'ta_sonrai_account',
    model,
)

class CustomAccountHandler(ConfigMigrationHandler):
    """
    This class handles the parameters in the account page
    """

    def __init__(self, *args, **kwargs):
        ConfigMigrationHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, conf_info):
        """
        This method is called when account is deleted. It deletes the account if it is not used in the input configurations.
        :param conf_info: The directory containing configurable parameters.
        """
        session_key = self.getSessionKey()
        stanza_name = self.callerArgs.id
        account_stanza = utility.read_conf_file(session_key, "ta_sonrai_account", stanza_name)
        try:
            response_status, response_content = rest.simpleRequest("/servicesNS/nobody/" + str(ta_sonrai_declare.ta_name) + "/configs/conf-inputs/", sessionKey=session_key, getargs={"output_mode": "json"}, raiseAllErrors=True)
            res = json.loads(response_content)
            input_list = []
            if "entry" in res:
                for inputs in res["entry"]:
                    if "name" in inputs:
                        input_name = (inputs["name"]).replace("sonrai_tickets_input://", "")
                        if "content" in inputs and "sonrai_account" in inputs["content"]:
                            global_account = inputs["content"]["sonrai_account"]
                            if global_account == stanza_name:
                                input_list.append(input_name)
            if input_list:
                raise RestError(409, "Cannot delete the account as it is already been used in {}.".format(", ".join(input_list)))
        except Exception as e:
            raise RestError(409, "Something went wrong while deleting the account.{}".format(str(e)))

        super(CustomAccountHandler, self).handleRemove(conf_info)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomAccountHandler,
    )
