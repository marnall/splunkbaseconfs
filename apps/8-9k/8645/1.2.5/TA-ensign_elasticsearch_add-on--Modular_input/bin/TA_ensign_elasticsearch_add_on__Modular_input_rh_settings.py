
import ta_ensign_elasticsearch_add_on_modular_input_declare

import logging as _log
import datetime as _dt

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

from checkbox_utils import CheckboxNormalizerMixin

util.remove_http_proxy_env_vars()


fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ), 
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=4096, 
        )
    ), 
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=1, 
            max_val=65535, 
        )
    ), 
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=50, 
        )
    ), 
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=False,  # Not encrypted: proxy is not used in this deployment.
        default=None,     # Storing as plaintext avoids CredentialNotExistException
        validator=validator.String(  # when no proxy credential has ever been saved.
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'proxy_rdns',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model_proxy = RestModel(fields_proxy, name='proxy')


fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')


# ─────────────────────────────────────────────────────────────────────────
# CHECKPOINT SETTINGS (v1.2.3)
# ─────────────────────────────────────────────────────────────────────────
fields_checkpoint = [
    field.RestField(
        'checkpoint_storage',
        required=False,
        encrypted=False,
        default='file',
        validator=validator.Enum(values=['file', 'kvstore'])
    )
]
model_checkpoint = RestModel(fields_checkpoint, name='checkpoint')


endpoint = MultipleModel(
    'ta_ensign_elasticsearch_add_on__modular_input_settings',
    models=[
        model_proxy, 
        model_logging,
        model_checkpoint,
    ],
)


class AuditableSettingsHandler(CheckboxNormalizerMixin, ConfigMigrationHandler):
    """Settings handler with 5W1H security audit logging.

    Also coerces UCC checkbox fields on the Proxy stanza
    ("proxy_enabled", "proxy_rdns") to the strict "0"/"1" wire format,
    so the UCC checkbox component renders the checked state correctly
    on Edit. Logging stanza has no checkbox fields; checkpoint stanza
    has no checkbox fields. Normalization is a no-op when the targeted
    fields are absent.
    """

    CHECKBOX_FIELDS = ("proxy_enabled", "proxy_rdns")

    def _audit(self, action, stanza, fields=""):
        _log.getLogger("TA-ensign_elasticsearch_add-on--Modular_input").info(
            f"[AUDIT] handler=settings action={action} "
            f"who={getattr(self, 'userName', 'unknown')} "
            f"when={_dt.datetime.utcnow().isoformat()}Z "
            f"what=settings_change which=stanza={stanza} how=fields={fields}"
        )

    def handleEdit(self, confInfo):
        self._normalize_payload()
        fields = ",".join((self.callerArgs.data or {}).keys())
        self._audit("EDIT", self.callerArgs.id or "?", fields)
        super().handleEdit(confInfo)

    def handleList(self, confInfo):
        super().handleList(confInfo)
        self._normalize_confinfo(confInfo)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AuditableSettingsHandler,
    )
