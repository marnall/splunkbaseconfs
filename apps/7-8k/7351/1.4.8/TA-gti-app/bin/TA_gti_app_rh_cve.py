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
        default=None,
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""",
        ),
    ),
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validators.ValidateCveIndex(),
    ),
    field.RestField(
        'risk_rating',
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        'exploitation_state',
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField('disabled', required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    'cve',
    model,
)


if __name__ == '__main__':
  logging.getLogger().addHandler(logging.NullHandler())
  admin_external.handle(
      endpoint,
      handler=AdminExternalHandler,
  )
