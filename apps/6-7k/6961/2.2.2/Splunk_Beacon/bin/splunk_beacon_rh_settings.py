import logging

import package_helper # keep for added paths
from splunktaucclib.rest_handler.endpoint import field, RestModel, MultipleModel, validator
from splunktaucclib.rest_handler.endpoint import converter as conv
from splunktaucclib.rest_handler import admin_external, util
from urllib.parse import urlparse

util.remove_http_proxy_env_vars()

def _validate_enable_requires_url(value, data, *args, **kwargs):
    """
    When enable_proxy is truthy, https_proxy_url must be provided.
    """
    is_enabled = str(value).strip() in ("1", "true", "True")
    if is_enabled:
        url = (data.get("https_proxy_url") or "").strip()
        if not url:
            raise validator.ValidationFailed("Please provide the HTTPS proxy URL")
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise validator.ValidationFailed("Please enter a full proxy URL like https://host:port")
        if parsed.scheme not in ("http", "https"):
            raise validator.ValidationFailed("Proxy URL must start with http:// or https://")

fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=validator.Enum(
            values=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']
        )
    )
]

fields_proxy = [
    field.RestField(
        'enable_proxy',
        required=False,
        encrypted=False,
        default='0',
        converter=conv.Boolean(default=False),
    ),
    field.RestField(
        'https_proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.UserDefined(_validate_enable_requires_url),
    ),
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=None,
    ),
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=None,
    ),
]

endpoint = MultipleModel(
    'splunk_beacon_settings',
    models=[
        RestModel(fields_logging, name='logging'),
        RestModel(fields_proxy, name='proxy'),
    ],
)

if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(endpoint)
