import ta_sophos_central_addon_for_splunk_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler.error import RestError
import sophos_common_utils as utils
from sophos_collect import SophosCollect
from log_manager import setup_logging

_LOGGER = setup_logging("sophos_tenant_input")

util.remove_http_proxy_env_vars()


class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """Extended custom input config handler."""

    def handleCreate(self, conf_info):
        """To override the input creation process."""
        session_key = self.getSessionKey()

        # Initialize SophosCollect Object
        collect_obj = SophosCollect(session_key)
        try:
            collect_obj.check_credentials()
            all_inputs = utils.read_conf_file(session_key, "inputs")

            conf_params = utils.get_sophos_config_params(session_key)
            account_type = conf_params["account_id_type"]
            # _LOGGER.info("conf_params account_type :{}".format(conf_params["account_id_type"]))
            # _LOGGER.info("collect_obj.SOPHOS_CONFIGS account_type :{}".format(collect_obj.SOPHOS_CONFIGS.get("account_id_type")))

            if account_type == "tenant":
                raise RestError("405", str("Tenant input configuration is not required since the credential is a tenant credential. Proceed with the creation of alert, endpoint, and event inputs."))

            # check if input with same index already exists to prevent data duplication.
            for input, input_meta in all_inputs.items():
                if input.startswith("sophos_tenant_input://") and input_meta.get("index") == self.payload.get("index"):
                    raise RestError("500", f"Tenant input with index '{self.payload.get('index')}' already exists.")
        except Exception as e:
            raise RestError("500", str(e))
        super(CustomConfigMigrationHandler, self).handleCreate(conf_info)


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=3600,
            max_val=172800,
        ),
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
        "page_limit",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=51,
        ),
    ),
    field.RestField(
        "type",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=51,
        ),
    ),
    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'sophos_tenant_input',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )
