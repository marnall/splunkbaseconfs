
import import_declare_test  # noqa

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import splunk.admin as admin
from cymru_helpers.validators import AccountValidator
from cymru_helpers.conf_helper import get_conf_file
from cymru_helpers.logger_manager import setup_logging
import logging
import traceback

util.remove_http_proxy_env_vars()


class CymruSettingsHandler(AdminExternalHandler):
    """Class for account handling."""

    def __init__(self, *args, **kwargs):
        """Init method for class."""
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleRemove(self, confInfo):
        """Defined method to Remove account."""
        try:
            acc_name = self.callerArgs.id
            logger = setup_logging('ta_team_cymru_feed_account_deletion', account_name=acc_name)
            logger.info("Account Deletion started.")
            conf_file = get_conf_file(
                file="inputs",
                session_key=self.getSessionKey(),
            )
            inputs_file = conf_file.get_all(only_current_app=True)
            created_inputs = list(inputs_file.keys())
            input_list = []

            for _input in created_inputs:
                cymru_input = _input.split('://')
                if cymru_input[0] == "cymru_feed_api":
                    configured_account = inputs_file.get(_input).get('account')
                    if configured_account == acc_name:
                        input_list.append(cymru_input[1])
            if len(input_list) > 0:
                raise admin.ArgValidationException(
                    "Account \"{}\" can not be deleted because it is in use by the following inputs: {}".format(
                        acc_name, input_list
                    )
                )
            else:
                super(CymruSettingsHandler, self).handleRemove(confInfo)
                logger.info("Account Deleted Successfully.")

        except Exception as e:
            logger.error(
                "message=account_deletion_error | "
                "Team Cymru account deletion Error occured \"{}\"".format(
                    traceback.format_exc()
                )
            )
            raise admin.ArgValidationException(e)


fields = [
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
        validator=AccountValidator()
    )
]
model = RestModel(fields, name=None)


endpoint = SingleModel(
    'TeamCymruFeedAppForSplunk_account',
    model,
    config_name='account'
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CymruSettingsHandler,
    )
