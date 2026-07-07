
import ta_risksense_declare
from account_validation import AccountValidator
from splunk_aoblib.rest_migration import ConfigMigrationHandler


from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util

util.remove_http_proxy_env_vars()


class AccountModel(SingleModel):
    # Override validate method to add name parameter
    def validate(self, name, data, existing=None):
        """
        Add name parameter before validation and add client_id parameter after validation

        :param name: Name of the Global Account
        :param data: Global Account dictionary
        :param existing: Other kwargs

        """
        data_to_validate = data.copy()
        data_to_validate['name'] = name
        is_valid = super(AccountModel, self).validate(
            name, data_to_validate, existing)
        data['client_id'] = data_to_validate.get('client_id')
        return is_valid


fields = [
    field.RestField(
        'token',
        required=True,
        encrypted=True,
        default=None,
        validator=AccountValidator()
    ),
    field.RestField(
        'platform_url',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'client_name',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'client_id',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),
]
model = RestModel(fields, name=None)

endpoint = AccountModel(
    'ta_risksense_account',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
