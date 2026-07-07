# pylint: disable=missing-module-docstring
# pylint: disable=invalid-name
import import_declare_test  # pylint: disable=unused-import

from gti.core import validators
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=3600,
        validator=validators.ValidateInterval(),
    ),
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1,
            max_len=80,
        ),
    ),
    field.RestField(
        'threat_lists_category',
        required=True,
        encrypted=False,
        default=None,
        validator=validators.ValidateThreatListsCategory(),
    ),
    field.RestField(
        'threat_lists_filter',
        required=False,
        encrypted=False,
        default='',
        validator=validators.ValidateThreatListsFilter(),
    ),
    field.RestField(
        'sync_es_threat_intelligence',
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField('disabled', required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    'threat_lists',
    model,
)


if __name__ == '__main__':
  logging.getLogger().addHandler(logging.NullHandler())
  admin_external.handle(
      endpoint,
      handler=AdminExternalHandler,
  )
