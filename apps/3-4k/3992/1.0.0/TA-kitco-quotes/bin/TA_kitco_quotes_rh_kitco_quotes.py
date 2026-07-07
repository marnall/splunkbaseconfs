
import ta_kitco_quotes_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^\-[1-9]\d*$|^\d*$""", 
        )
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
        'precious_metals',
        required=False,
        encrypted=False,
        default='GOLD~PLATINUM~PALLADIUM~RHODIUM~SILVER',
        validator=None
    ), 
    field.RestField(
        'base_metals',
        required=False,
        encrypted=False,
        default='ALUMINUM~COPPER~NICKEL~LEAD~ZINC',
        validator=None
    ), 
    field.RestField(
        'currencies',
        required=False,
        encrypted=False,
        default='BRL~AUD~CHF~CAD~CNY~EUR~HKD~GBP~INR~JPY~MXN~RUB~ZAR',
        validator=None
    ), 
    field.RestField(
        'other',
        required=False,
        encrypted=False,
        default='OIL~DJIA~USDX~SP500~NYSE~NIKKEI~HUI~TSX~XAU',
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
    'kitco_quotes',
    model,
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
