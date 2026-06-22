import ta_ensign_elasticsearch_add_on_modular_input_declare
import splunk.rest as rest
import json
import logging as _log
import datetime as _dt
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler

from checkbox_utils import CheckboxNormalizerMixin

class InUseValidator(validator.Validator):
    def validate(self, value, data):
        # We only care when the item is being disabled or deleted
        # 'data' contains the payload being saved.
        # But wait, how do we get the name of the stanza being updated?
        # In custom UCC Validators, 'data' is a dict of the fields. 
        # The stanza name is often in the URI or `self._name`.
        # UCC passes `data['name']` as the stanza name.
        stanza_name = data.get('name', '')
        if not stanza_name:
            return True

        is_disabled = str(data.get('disabled', '0')).lower() in ['1', 'true', 'yes']
        if not is_disabled:
            return True # Not being disabled, safe to proceed

        # Check if disabled, query all data inputs!
        # `data.get('session_key')` is securely passed by UCC sometimes, or we can use our own context workaround if needed, 
        # but UCC validators usually don't have session_key injected into `data`.
        # Actually, in UCC, you can trigger API via `splunk.rest.simpleRequest`.
        try:
            # We can use the global daemon token if standard context isn't available, but let's try standard rest endpoint.
            # `admin_external` context usually runs as splunk-system-user.
            uri = '/servicesNS/nobody/TA-ensign_elasticsearch_add-on--Modular_input/data/inputs/elasticsearch_source?output_mode=json'
            response, content = rest.simpleRequest(uri, method='GET')
            if response.status == 200:
                payload = json.loads(content)
                in_use_inputs = []
                for entry in payload.get('entry', []):
                    content = entry.get('content', {})
                    if content.get('es_cluster_target') == stanza_name and str(content.get('disabled', '0')) != '1':
                        in_use_inputs.append(entry.get('name'))
                
                if in_use_inputs:
                    self.put_msg(f"[-] ACTION DENIED: Configuration '{stanza_name}' is currently in active use by the following Data Input(s): [{', '.join(in_use_inputs)}]. Please disable those inputs first before proceeding.")
                    return False
        except Exception as e:
            # If API fails, safety first: don't block randomly, or log it
            pass
        return True


fields = [
    field.RestField(
        'es_host',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(max_len=8192)
    ),
    field.RestField(
        'es_port',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(max_len=8192)
    ),
    field.RestField(
        'es_user',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(max_len=8192)
    ),
    field.RestField(
        'es_pass',
        required=True,
        encrypted=True,
        default=None,
        validator=validator.String(max_len=8192)
    ),
    field.RestField(
        'verify_cert',
        required=False,
        encrypted=False,
        default='1',
        validator=None
    ),
    field.RestField(
        'cert_location',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(max_len=8192)
    ),
    # ───────────────────────────────────────────────────────────
    # CLUSTER-AWARE FIELDS (v1.2.0)
    # ───────────────────────────────────────────────────────────
    field.RestField(
        'enable_sniffing',
        required=False,
        encrypted=False,
        default='0',
        validator=None
    ),
    field.RestField(
        'max_retries',
        required=False,
        encrypted=False,
        default='3',
        validator=validator.String(max_len=8192)
    ),
    field.RestField(
        'retry_on_timeout',
        required=False,
        encrypted=False,
        default='1',
        validator=None
    ),
    field.RestField(
        'connection_timeout',
        required=False,
        encrypted=False,
        default='30',
        validator=validator.String(max_len=8192)
    ),
    field.RestField(
        'disabled',
        required=False,
        validator=InUseValidator()
    )
]

model = RestModel(fields, name=None)

endpoint = SingleModel(
    'ta_ensign_elasticsearch_add_on__modular_input_es_clusters',
    model,
)

class SpaceToUnderscoreHandler(ConfigMigrationHandler):
    def handleCreate(self, confInfo):
        if self.callerArgs and self.callerArgs.id:
            self.callerArgs.id = self.callerArgs.id.replace(' ', '_')
        super(SpaceToUnderscoreHandler, self).handleCreate(confInfo)

class AuditableClusterHandler(CheckboxNormalizerMixin, SpaceToUnderscoreHandler):
    """ES Clusters handler with 5W1H security audit logging.

    Also coerces UCC checkbox fields ("verify_cert", "enable_sniffing",
    "retry_on_timeout") to the strict "0"/"1" wire format on both read and
    write paths, so the UCC React checkbox component renders the checked
    state correctly when a cluster profile is re-opened for Edit.
    """

    CHECKBOX_FIELDS = ("verify_cert", "enable_sniffing", "retry_on_timeout")

    def _audit(self, action, stanza, extra=""):
        data = self.callerArgs.data or {}
        # SECURITY: Never log es_pass value
        safe_fields = [f if f != "es_pass" else "es_pass=REDACTED" for f in data.keys()]
        _log.getLogger("TA-ensign_elasticsearch_add-on--Modular_input").info(
            f"[AUDIT] handler=es_clusters action={action} "
            f"who={getattr(self, 'userName', 'unknown')} "
            f"when={_dt.datetime.utcnow().isoformat()}Z "
            f"what=cluster_config which=stanza={stanza} "
            f"how={extra or ','.join(safe_fields)}"
        )

    def handleCreate(self, confInfo):
        self._normalize_payload()
        data = self.callerArgs.data or {}
        host = data.get("es_host", ["?"])[0]
        port = data.get("es_port", ["?"])[0]
        self._audit("CREATE", self.callerArgs.id or "?",
                    f"es_host={host},es_port={port},es_pass=REDACTED")
        super().handleCreate(confInfo)

    def handleEdit(self, confInfo):
        self._normalize_payload()
        self._audit("EDIT", self.callerArgs.id or "?")
        super().handleEdit(confInfo)

    def handleList(self, confInfo):
        super().handleList(confInfo)
        self._normalize_confinfo(confInfo)

    def handleRemove(self, confInfo):
        self._audit("DELETE", self.callerArgs.id or "?", "cluster_removed=true")
        super().handleRemove(confInfo)


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=AuditableClusterHandler,
    )
