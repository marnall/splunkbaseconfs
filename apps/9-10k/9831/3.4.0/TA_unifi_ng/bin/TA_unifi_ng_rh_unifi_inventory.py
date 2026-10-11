
import import_declare_test

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


def _toggle(name, default=True):
    return field.RestField(
        name,
        required=False,
        encrypted=False,
        default=default,
        validator=None,
    )


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z]\w*$""",
            ),
            validator.String(
                max_len=100,
                min_len=1,
            )
        )
    )
]

fields = [
    field.RestField(
        'account',
        required=True,
        encrypted=False,
        default=None,
        validator=None
    ),
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='180',
        validator=validator.Pattern(
            regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""",
        )
    ),
    field.RestField(
        'index',
        required=False,
        encrypted=False,
        default='default',
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z0-9][a-zA-Z0-9\\_\\-]*$""",
            ),
            validator.String(
                max_len=80,
                min_len=1,
            )
        )
    ),
    # inventory collectors (defaults mirror plan §6b)
    _toggle('collect_devices', True),
    _toggle('collect_clients', True),
    _toggle('collect_networks', True),
    _toggle('collect_device_tags', True),
    _toggle('collect_firewall', True),
    _toggle('collect_wifi', True),
    _toggle('collect_wan', True),
    _toggle('collect_pending_devices', True),
    _toggle('collect_info', True),
    _toggle('collect_vpn', False),
    _toggle('collect_switching', False),
    _toggle('collect_dns', False),
    _toggle('collect_traffic_lists', False),
    _toggle('collect_radius', False),
    _toggle('collect_vouchers', False),
    _toggle('collect_network_detail', False),
    field.RestField(
        'page_size',
        required=False,
        encrypted=False,
        default='200',
        validator=validator.Number(
            max_val=200,
            min_val=1,
            is_int=True,
        )
    ),
    field.RestField(
        'collection_timeout',
        required=False,
        encrypted=False,
        default='120',
        validator=validator.Number(
            max_val=3600,
            min_val=10,
            is_int=True,
        )
    ),
    field.RestField(
        'site_ids',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ),

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = DataInputModel(
    'unifi_inventory',
    model,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
