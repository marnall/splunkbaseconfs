
import ta_purestorage_unified_declare  # noqa:   401
from purestorage_common_validations import (
    ValidateStartDate,
    ValidateInterval,
    ValidateIndexLength
)
from splunktaucclib.rest_handler.endpoint import (
    field,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from TA_purestorage_unified_input_type import InputType

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=ValidateInterval(
            regex=r"""^\-[1-9]\d*$|^\d*$""",
        )
    ),
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=ValidateIndexLength(
            min_len=1,
            max_len=80,
        )
    ),
    field.RestField(
        'input_type',
        required=True,
        encrypted=False,
        default='flashblade',
        validator=None
    ),
    field.RestField(
        'global_account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'start_date',
        required=True,
        encrypted=False,
        default=None,
        validator=ValidateStartDate()
    ),
    field.RestField(
        'disabled',
        required=False,
        validator=None
    ),
    field.RestField(
        'historical_data',
        required=False,
        validator=None,
        default="0"
    )

]
model = RestModel(fields, name=None)


endpoint = DataInputModel(
    'purestorage_unified_input',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=InputType,
    )
