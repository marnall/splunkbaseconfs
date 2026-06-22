
import ta_ensign_elasticsearch_add_on_modular_input_declare

import logging as _log
import datetime as _dt

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    DataInputModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

from checkbox_utils import CheckboxNormalizerMixin

util.remove_http_proxy_env_vars()


# ─────────────────────────────────────────────────────────────────────────
# MINIMUM INTERVAL VALIDATOR (v1.2.3)
# ─────────────────────────────────────────────────────────────────────────
class MinIntervalValidator(validator.Validator):
    """
    Validates that the polling interval is a positive integer and
    meets the minimum threshold of 15 seconds. This prevents
    resource exhaustion and checkpoint race conditions.
    """
    MIN_INTERVAL = 15

    def validate(self, value, data):
        try:
            interval = int(value)
        except (TypeError, ValueError):
            self.put_msg(
                f"Interval must be a positive integer (seconds). Got: '{value}'"
            )
            return False
        if interval < self.MIN_INTERVAL:
            self.put_msg(
                f"[-] Interval too low! Minimum allowed interval is "
                f"{self.MIN_INTERVAL} seconds. Got: {interval}s. "
                f"Please set interval >= {self.MIN_INTERVAL} in your "
                f"inputs.conf or via the UI."
            )
            return False
        return True


fields = [
    field.RestField(
        'interval',
        required=True,
        encrypted=False,
        default='30',
        validator=MinIntervalValidator()
    ), 
    field.RestField(
        'index',
        required=True,
        encrypted=False,
        default='default',
        validator=validator.String(
            min_len=1, 
            max_len=80, 
        )
    ), 
    field.RestField(
        'es_cluster_target',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=1, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'es_index',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 

    field.RestField(
        'time_preset',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'date_field',
        required=True,
        encrypted=False,
        default='@timestamp',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'enable_filter',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'filter_key',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'filter_val',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0,
            max_len=8192,
        )
    ),
    field.RestField(
        'enable_srctype',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'custom_srctype',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 

    field.RestField(
        'disabled',
        required=False,
        validator=None
    )

]
model = RestModel(fields, name=None)



endpoint = DataInputModel(
    'elasticsearch_source',
    model,
)


class SpaceToUnderscoreHandler(ConfigMigrationHandler):
    def handleCreate(self, confInfo):
        if self.callerArgs and self.callerArgs.id:
            self.callerArgs.id = self.callerArgs.id.replace(' ', '_')
        super(SpaceToUnderscoreHandler, self).handleCreate(confInfo)

class AuditableInputHandler(CheckboxNormalizerMixin, SpaceToUnderscoreHandler):
    """Data inputs handler with 5W1H security audit logging.

    Also coerces UCC checkbox fields ("enable_filter", "enable_srctype") to
    the strict "0"/"1" wire format on both read and write paths, so the UCC
    React checkbox component renders the checked state correctly when an
    input is re-opened for Edit.
    """

    CHECKBOX_FIELDS = ("enable_filter", "enable_srctype")

    def _audit(self, action, stanza, extra=""):
        _log.getLogger("TA-ensign_elasticsearch_add-on--Modular_input").info(
            f"[AUDIT] handler=elasticsearch_source action={action} "
            f"who={getattr(self, 'userName', 'unknown')} "
            f"when={_dt.datetime.utcnow().isoformat()}Z "
            f"what=input_config which=stanza={stanza} how={extra}"
        )

    def handleCreate(self, confInfo):
        self._normalize_payload()
        d = self.callerArgs.data or {}
        self._audit("CREATE", self.callerArgs.id or "?",
            f"cluster={d.get('es_cluster_target', ['?'])[0]},"
            f"es_index={d.get('es_index', ['?'])[0]},"
            f"interval={d.get('interval', ['?'])[0]}")
        super().handleCreate(confInfo)

    def handleEdit(self, confInfo):
        self._normalize_payload()
        fields = ",".join((self.callerArgs.data or {}).keys())
        self._audit("EDIT", self.callerArgs.id or "?", f"fields={fields}")
        super().handleEdit(confInfo)

    def handleList(self, confInfo):
        super().handleList(confInfo)
        self._normalize_confinfo(confInfo)

    def handleRemove(self, confInfo):
        self._audit("DELETE", self.callerArgs.id or "?", "input_removed=true")
        super().handleRemove(confInfo)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AuditableInputHandler,
    )
