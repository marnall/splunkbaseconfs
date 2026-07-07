import ta_threatquotient_add_on_declare

import json

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler.error import RestError
from solnlib.utils import is_true
from threatq_utils import validate_configured_input

import splunk.rest as rest
from splunk import ResourceNotFound

util.remove_http_proxy_env_vars()


class CustomConfigMigrationHandler(ConfigMigrationHandler):
    """Extended custom input config handler."""

    def transform_boolean_field_values(self):
        if is_true(self.payload.get("checkbox_for_index")):
            self.payload["checkbox_for_index"] = "true"
        else:
            self.payload["checkbox_for_index"] = "false"

        if is_true(self.payload.get("pull_all_iocs")):
            self.payload["pull_all_iocs"] = "true"
        else:
            self.payload["pull_all_iocs"] = "false"

    def handleCreate(self, conf_info):
        # post the initial pull_all_iocs flag value to the kvstore
        # this will override the input creation process
        self.transform_boolean_field_values()
        session_key = self.getSessionKey()
        try:
            validate_configured_input(session_key)
        except Exception as e:
            raise RestError("409", str(e))

        if not is_true(self.payload.get("pull_all_iocs")):
            raise RestError("409", "Enable 'Pull All Indicators' checkbox when creating input")

        super(CustomConfigMigrationHandler, self).handleCreate(conf_info)

    def handleEdit(self, conf_info):
        self.transform_boolean_field_values()

        super(CustomConfigMigrationHandler, self).handleEdit(conf_info)


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=900,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^\-[1-9]\d*$|^\d*$""",
            ),
            validator.Number(
                max_val=7200, 
                min_val=60, 
            )
        )
    ),
    field.RestField(
        'checkbox_for_index',
        required=False,
        encrypted=False,
        default=None,
        validator=None
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
        'export_id',
        required=True,
        encrypted=False,
        default="splunk",
        validator=validator.Pattern(
            regex=r"^\w+$",
        )
    ),
    field.RestField(
        'export_token',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"^\w+$",
        )
    ),
    field.RestField(
        'export_hash',
        required=True,
        encrypted=False,
        default="1",
        validator=validator.Pattern(
           regex=r"^[a-zA-Z0-9]+$",
        )
    ),
    field.RestField(
        'threshold_score',
        required=True,
        encrypted=False,
        default=8,
        validator=validator.Number(
            min_val=0,
            max_val=10,
        )
    ),
    field.RestField(
        'indicator_status',
        required=True,
        encrypted=False,
        default='Active',
        validator=None
    ),
    field.RestField(
        'pull_all_iocs',
        required=False,
        encrypted=False,
        default=True,
        validator=None
    ),
    field.RestField(
        'response_page_size',
        required=True,
        encrypted=False,
        default=10000,
        validator=None
    ),
    field.RestField(
        'disabled',
        required=False,
        validator=None
    )
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    'threatq_indicators',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=CustomConfigMigrationHandler,
    )
