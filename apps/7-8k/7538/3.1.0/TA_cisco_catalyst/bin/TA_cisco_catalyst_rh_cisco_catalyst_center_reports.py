"""Catalyst Center Reports Input rest handler file."""
import import_declare_test  # noqa: F401

import logging

from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    DataInputModel,
    RestModel,
    field,
    validator
)

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
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
            max_len=80,
            min_len=1,
        )
    ),
    field.RestField(
        'cisco_dna_center_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'inventory_report_name',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'compliance_report_name',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ),
    field.RestField(
        'logging_level',
        required=False,
        encrypted=False,
        default='INFO',
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
    'cisco_catalyst_center_reports',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )