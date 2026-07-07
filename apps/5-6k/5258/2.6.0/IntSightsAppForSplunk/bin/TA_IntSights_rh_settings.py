
import ta_intsights_declare
import os

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from intsights_utils import verify_authentication, get_proxy_info
from macros_configuration import CorrelationValidator
from solnlib import conf_manager
from log_manager import setup_logging
import macros_ui_constants as consts
import constants as const
logger_name = os.path.splitext(os.path.basename(__file__))[0]
logger = setup_logging(logger_name)

util.remove_http_proxy_env_vars()


def get_conf_file(file, app, session_key=None, stanza=None, realm="__REST_CREDENTIAL__#{}#configs/conf-{}"): # noqa E502
    """Returns the content of conf file."""
    cfm = conf_manager.ConfManager(session_key, app, realm=realm.format(app, file)).get_conf(file)
    if stanza:
        return cfm.get(stanza)
    return cfm

def write_to_conf_file(file, stanza_name, stanza, app, session_key=None, realm="__REST_CREDENTIAL__#{}#configs/conf-{}"): # noqa E502
    """Updates the content of conf file."""
    cfm = conf_manager.ConfManager(session_key, app, realm=realm.format(app, file))
    conf = cfm.get_conf(file)
    return conf.update(stanza_name, stanza)

class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """
    Manage the Rest Handler for server
    :param ConfigMigrationHandler: inheriting ConfigMigrationHandler
    """
    def handleList(self, confInfo):
        """handleList method of Splunk."""    
        try:
            macros_data = get_conf_file(file="macros", app=const.TA_NAME, session_key=SessionKeyProvider().session_key)
            final_data = {}
            for key, value in consts.ALL_MACROS_WITH_UI_FIELD.items():              
                if key in ("enable_tags_comments_api_calls", "enable_maintain_corr_indexes_actions"):
                    final_data[key] = "true" if macros_data.get(value).get("definition") in [True, "True", "true", 1, "1"] else "false"
                else:
                    final_data[key] = macros_data.get(value).get("definition")
            write_to_conf_file(file="ta_intsights_settings", stanza_name="additional_parameters", stanza=final_data, app=const.TA_NAME, session_key=SessionKeyProvider().session_key)
            super(CustomConfigMigrationHandler, self).handleList(confInfo)
        except Exception as err:
            logger.error("Error occured while updating ta_intsights_settings.conf file = {}".format(err))


class SessionKeyProvider(ConfigMigrationHandler):
    def __init__(self):
        self.session_key = self.getSessionKey()


class Account(validator.Validator):
    def __init__(self):
        super(Account, self).__init__()

    def validate(self, value, data):
        session_key = SessionKeyProvider().session_key
        proxies = get_proxy_info(session_key)
        try:
            verify_authentication(data, proxies)
            return True
        except Exception as e:
            self.put_msg(e)
            return False

fields_account = [
    field.RestField(
        'server_address',
        required=True,
        encrypted=False,
        default="api.intsights.com",
        validator=validator.Pattern(
            regex="^(?!\\w+:\\/\\/).*",
        )
    ),
    field.RestField(
        'account_id',
        required=True,
        encrypted=False,
        default=None,
        validator=Account()
    ),
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=8192,
        )
    )
]

model_account = RestModel(fields_account, name="account")


fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ),
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=4096, 
        )
    ),
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=1, 
            max_val=65535, 
        )
    ), 
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=50, 
        )
    ), 
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    )
]
model_proxy = RestModel(fields_proxy, name='proxy')


fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_additional_parameters = [
    field.RestField(
        'selected_input_type',
        required=False,
        encrypted=False,
        default="ioc",
        validator=CorrelationValidator()
    ),
    field.RestField(
        "alert_indices",
        required=False,
        encrypted=False,
        default='(index="main")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "vuln_indices",
        required=False,
        encrypted=False,
        default='(index="main")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "vuln_target_indices",
        required=False,
        encrypted=False,
        default='(index="main")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "vuln_target_sourcetypes",
        required=False,
        encrypted=False,
        default='(sourcetype="*")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "emails_target_indices",
        required=False,
        encrypted=False,
        default='(index="main")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "emails_target_sourcetypes",
        required=False,
        encrypted=False,
        default='(sourcetype="*")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "emails_target_ioc_fields",
        required=False,
        encrypted=False,
        default='"email"',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "vuln_target_indicator_fields",
        required=False,
        encrypted=False,
        default='"signature", "signature_id", "cert", "cve"',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "ioc_type_value",
        required=False,
        encrypted=False,
        default="",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "ips_target_indices",
        required=False,
        encrypted=False,
        default='(index="main")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "domains_target_ioc_fields",
        required=False,
        encrypted=False,
        default='"domain"',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "domains_target_action_fields",
        required=False,
        encrypted=False,
        default=",",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "urls_target_indices",
        required=False,
        encrypted=False,
        default='(index="main")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "emails_target_action_fields",
        required=False,
        encrypted=False,
        default=",",
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "domains_target_indices",
        required=False,
        encrypted=False,
        default='(index="main")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "domains_target_sourcetypes",
        required=False,
        encrypted=False,
        default='(sourcetype="*")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "ips_target_sourcetypes",
        required=False,
        encrypted=False,
        default='(sourcetype="*")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "ips_target_ioc_fields",
        required=False,
        encrypted=False,
        default='"src_ip", "dest_ip"',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "ips_target_action_fields",
        required=False,
        encrypted=False,
        default=',',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "urls_target_sourcetypes",
        required=False,
        encrypted=False,
        default='(sourcetype="*")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "urls_target_ioc_fields",
        required=False,
        encrypted=False,
        default='"url"',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "urls_target_action_fields",
        required=False,
        encrypted=False,
        default=',',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "hashes_target_indices",
        required=False,
        encrypted=False,
        default='(index="main")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "hashes_target_sourcetypes",
        required=False,
        encrypted=False,
        default='(sourcetype="*")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "hashes_target_ioc_fields",
        required=False,
        encrypted=False,
        default='"file_hash"',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "hashes_target_action_fields",
        required=False,
        encrypted=False,
        default=',',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "ioc_indices",
        required=False,
        encrypted=False,
        default='(index="main")',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        "enable_tags_comments_api_calls",
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        "enable_maintain_corr_indexes_actions",
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model_additional_parameters = RestModel(
    fields_additional_parameters, name="additional_parameters"
)


endpoint = MultipleModel(
    'ta_intsights_settings',
    models=[
        model_account,
        model_proxy, 
        model_logging,
        model_additional_parameters,
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )
