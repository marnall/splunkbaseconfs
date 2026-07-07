import ta_sophos_central_addon_for_splunk_declare

import os.path as op
from solnlib.modular_input import checkpointer
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler.error import RestError
from sophos_collect import SophosCollect
import sophos_common_utils as utils
from log_manager import setup_logging

_LOGGER = setup_logging("sophos_endpoint_input")

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

            if account_type in ["partner", "organisation"]:
                no_of_tenant_inputs = 0
                for each_input in all_inputs.keys():
                    if each_input.startswith('sophos_tenant_input://'):
                        no_of_tenant_inputs = no_of_tenant_inputs + 1
                
                if no_of_tenant_inputs == 0:
                    raise RestError("500", str("Tenant input configuration is required to create this input."))
            
            # check if input with same index already exists to prevent data duplication.
            for input, input_meta in all_inputs.items():
                if input.startswith("sophos_endpoint_input://") and input_meta.get("index") == self.payload.get("index"):
                    raise RestError("500", f"Endpoint input with index '{self.payload.get('index')}' already exists.")
        except Exception as e:
            raise RestError("500", str(e))
        super(CustomConfigMigrationHandler, self).handleCreate(conf_info)


fields = [
    field.RestField(
        "interval",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=3600,
            max_val=86400,
        ),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.String(
            min_len=1,
            max_len=80,
        ),
    ),
    field.RestField(
        "page_limit",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1,
            max_len=501,
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
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    "sophos_endpoint_input",
    model,
)


if __name__ == "__main__":
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )
