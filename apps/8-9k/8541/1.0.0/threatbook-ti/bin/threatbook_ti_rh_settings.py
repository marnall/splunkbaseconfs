"""REST Handler for ThreatBook TI App settings."""

import json

import threatbook_ti_declare  # noqa: F401
from threatbook_ti.core import constants

from splunktaucclib.rest_handler.endpoint import (
    converter,
    field,
    validator,
    RestModel,
    MultipleModel,
)

from splunktaucclib.rest_handler import admin_external, util


def _bool_encode(value, data):
    return 'true' if str(value).lower() in ('true', '1', 'yes') else 'false'


def _bool_decode(value, data):
    return 'true' if str(value).lower() in ('true', '1', 'yes') else 'false'


_BOOL_CONV = converter.UserDefined(encoder=_bool_encode, decoder=_bool_decode)

_GLOBAL_EXCLUDE_TO_STORAGE = {
    'threat_types': 'judgments',
    'intel_labels': 'tags_classes',
}
_GLOBAL_EXCLUDE_TO_UI = {v: k for k, v in _GLOBAL_EXCLUDE_TO_STORAGE.items()}


def _transform_global_exclude(value, data, value_map):
    del data

    if value in (None, ''):
        return value

    parsed = value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return value

    if not isinstance(parsed, list):
        return value

    return json.dumps(
        [value_map.get(item, item) for item in parsed],
        ensure_ascii=False,
        separators=(',', ':'),
    )


def _encode_global_exclude(value, data):
    return _transform_global_exclude(value, data, _GLOBAL_EXCLUDE_TO_STORAGE)


def _decode_global_exclude(value, data):
    return _transform_global_exclude(value, data, _GLOBAL_EXCLUDE_TO_UI)


_GLOBAL_EXCLUDE_CONV = converter.UserDefined(_encode_global_exclude, _decode_global_exclude)

util.remove_http_proxy_env_vars()


def _validate_proxy_payload_special(value, data, *args, **kwargs):
    del value, args, kwargs

    required = ['proxy_enabled']
    missing = [k for k in required if k not in data]
    if missing:
        raise validator.ValidationFailed(
            'PROXY_CONFIG_INVALID: missing field {}'.format(','.join(missing))
        )

    if str(data.get('proxy_enabled', '')).strip().lower() not in ('true', '1', 'yes'):
        return

    enabled_required = [
        'proxy_type',
        'proxy_host',
        'proxy_port',
        'proxy_remote_dns',
    ]
    missing = [k for k in enabled_required if k not in data]
    if missing:
        raise validator.ValidationFailed(
            'PROXY_CONFIG_INVALID: missing field {}'.format(','.join(missing))
        )


# --- Proxy settings ---

fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default='false',
        converter=_BOOL_CONV,
        validator=None,
    ),
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=validator.Enum(['http', 'https', 'socks4', 'socks5']),
    ),
    field.RestField(
        'proxy_host',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=1024,
        ),
    ),
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default='8080',
        validator=validator.Number(
            min_val=1,
            max_val=65535,
            is_int=True,
        ),
    ),
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=100,
        ),
    ),
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=100,
        ),
    ),
    field.RestField(
        'proxy_remote_dns',
        required=False,
        encrypted=False,
        default='false',
        converter=_BOOL_CONV,
        validator=None,
    ),
]
model_proxy = RestModel(
    fields_proxy,
    name='proxy',
    special_fields=[
        field.RestField(
            '__proxy_payload_guard__',
            required=False,
            encrypted=False,
            default='',
            validator=validator.UserDefined(_validate_proxy_payload_special),
        )
    ],
)


# --- Logging settings ---

fields_logging = [
    field.RestField(
        constants.CONFIG_SYSTEM_LOG_LEVEL,
        required=False,
        encrypted=False,
        default='ERROR',
        validator=validator.Enum(['FATAL', 'CRITICAL', 'ERROR', 'INFO', 'DEBUG']),
    ),
    field.RestField(
        constants.CONFIG_AUDIT_ENABLED,
        required=False,
        encrypted=False,
        default='true',
        converter=_BOOL_CONV,
        validator=None,
    ),
]
model_logging = RestModel(fields_logging, name='logging')


# --- Basic settings ---

fields_basic = [
    field.RestField(
        constants.CONFIG_API_REGION,
        required=False,
        encrypted=False,
        default='china',
        validator=validator.Enum(['china', 'global']),
    ),
    field.RestField(
        constants.CONFIG_API_KEY_CHINA,
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        constants.CONFIG_API_KEY_GLOBAL,
        required=False,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=8192,
        ),
    ),
    field.RestField(
        constants.CONFIG_COMPROMISE_LANG,
        required=False,
        encrypted=False,
        default='EN',
        validator=validator.Enum(['EN', 'ZH']),
    ),
    field.RestField(
        constants.CONFIG_COMPROMISE_REALTIME_VERDICT,
        required=False,
        encrypted=False,
        default='false',
        validator=validator.Enum(['true', 'false']),
        converter=_BOOL_CONV,
    ),
    field.RestField(
        constants.CONFIG_IP_REPUTATION_LANG,
        required=False,
        encrypted=False,
        default='EN',
        validator=validator.Enum(['EN', 'ZH']),
    ),
    field.RestField(
        constants.CONFIG_IP_REPUTATION_REALTIME_VERDICT,
        required=False,
        encrypted=False,
        default='false',
        validator=validator.Enum(['true', 'false']),
        converter=_BOOL_CONV,
    ),
    field.RestField(
        constants.CONFIG_IP_INTELLIGENCE_EXCLUDE,
        required=False,
        encrypted=False,
        default='[]',
        converter=_GLOBAL_EXCLUDE_CONV,
        validator=validator.String(
            min_len=2,
            max_len=2048,
        ),
    ),
    field.RestField(
        constants.CONFIG_DOMAIN_INTELLIGENCE_EXCLUDE,
        required=False,
        encrypted=False,
        default='[]',
        converter=_GLOBAL_EXCLUDE_CONV,
        validator=validator.String(
            min_len=2,
            max_len=2048,
        ),
    ),
    field.RestField(
        constants.CONFIG_FILE_INTELLIGENCE_SANDBOX_TYPE,
        required=False,
        encrypted=False,
        default='',
        validator=validator.String(
            min_len=0,
            max_len=256,
        ),
    ),
]
model_basic = RestModel(fields_basic, name='basic')


# --- Cache settings ---

fields_cache = [
    field.RestField(
        constants.CONFIG_CACHE_POLICY,
        required=True,
        encrypted=False,
        default='store_all_successful_calls',
        validator=validator.Enum([
            'store_all_successful_calls',
            'store_malicious_suspicious_only',
        ]),
    ),
    field.RestField(
        constants.CONFIG_TTL_VALUE,
        required=True,
        encrypted=False,
        default='24',
        validator=validator.Number(
            min_val=1,
            max_val=8760,
            is_int=True,
        ),
    ),
    field.RestField(
        constants.CONFIG_AUTO_CLEANUP_ENABLED,
        required=True,
        encrypted=False,
        default='true',
        validator=validator.Enum(['true', 'false']),
        converter=_BOOL_CONV,
    ),
    field.RestField(
        constants.CONFIG_AUTO_CLEANUP_TIME,
        required=True,
        encrypted=False,
        default='90',
        validator=validator.Number(
            min_val=1,
            max_val=3650,
            is_int=True,
        ),
    ),
]
model_cache = RestModel(fields_cache, name='cache')


# --- Endpoint ---

endpoint = MultipleModel(
    constants.SETTINGS_FILE,
    models=[
        model_proxy,
        model_logging,
        model_basic,
        model_cache,
    ],
)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=admin_external.AdminExternalHandler,
    )
