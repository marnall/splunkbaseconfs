"""Provider preset metadata for the Setup / Provider editor UI.

Issue #18 (and caveat): the provider dropdown in the front-end was hard-coded
against a list of base URLs and model names that drifted from the backend
defaults. This endpoint serves a single source of truth.

Storage strategy (Issue #18 caveat):
  * Authoritative store is the ``mcp_provider_presets`` KV collection so an
    admin can add or remove models without releasing a new app build.
  * On a fresh install the collection is empty; we seed it lazily on first
    GET from the BUILT_IN_PRESETS constant below.
  * If the KV store is unreachable for any reason we fall back to
    BUILT_IN_PRESETS so the UI still works.

GET /servicesNS/nobody/AI_Query_Assistant_for_Splunk/admin/mcp_provider_presets
    -> {"presets": {"presets_json": "[ ... ]", "json": "[ ... ]", "count": "6", "source": "kv|builtin|seeded"}}

No license check — these are public, vendor-published facts (URLs and
model names) and we want the configuration UI to load even when the
license is absent or invalid.
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import splunk.admin as admin
from mcp_base import MCPBaseHandler
from kv_store import KVStoreClient, KVStoreError

logger = logging.getLogger(__name__)

COLLECTION = 'mcp_provider_presets'


# Field names align with the frontend parser in mcp_providers.js
# (`url`, `backend`, `model`, `models[]`). `provider_type` and `base_url` are
# also emitted as aliases for any future direct-API consumer that prefers the
# canonical Splunk-side field names used in mcp_ai_providers KV records.
def _preset(id_, label, backend, url, models):
    return {
        "id": id_,
        "label": label,
        "backend": backend,           # frontend reads this
        "provider_type": backend,     # alias for direct API consumers
        "url": url,                   # frontend reads this
        "base_url": url,              # alias
        "model": models[0] if models else "",  # default model for the dropdown
        "models": list(models),
    }


BUILT_IN_PRESETS = [
    _preset("openai", "OpenAI", "openai_compatible",
            "https://api.openai.com/v1",
            ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]),
    _preset("anthropic", "Anthropic", "anthropic",
            "https://api.anthropic.com/v1",
            ["claude-sonnet-4-20250514", "claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"]),
    _preset("deepseek", "DeepSeek", "openai_compatible",
            "https://api.deepseek.com/v1",
            ["deepseek-chat", "deepseek-coder"]),
    _preset("qwen", "Qwen (Alibaba)", "openai_compatible",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ["qwen-max", "qwen-turbo", "qwen-plus"]),
    _preset("doubao", "Doubao (ByteDance)", "openai_compatible",
            "https://ark.cn-beijing.volces.com/api/v3",
            ["doubao-pro-32k", "doubao-lite-32k"]),
    _preset("openai_compatible", "OpenAI Compatible (manual)", "openai_compatible",
            "", []),
]


def _record_to_preset(rec):
    """Coerce a KV record into the wire shape the frontend expects."""
    try:
        models = json.loads(rec.get('models_json') or '[]')
        if not isinstance(models, list):
            models = []
    except (TypeError, ValueError):
        models = []
    return _preset(
        rec.get('preset_id') or rec.get('_key') or '',
        rec.get('label') or rec.get('preset_id') or '',
        rec.get('backend') or 'openai_compatible',
        rec.get('url') or '',
        models or ([rec['model']] if rec.get('model') else []),
    )


def _preset_to_record(p):
    """Inverse: convert a wire-shape preset to the flat KV record schema."""
    return {
        '_key': p['id'],
        'preset_id': p['id'],
        'label': p.get('label', p['id']),
        'backend': p.get('backend', 'openai_compatible'),
        'url': p.get('url', ''),
        'model': p.get('model', ''),
        'models_json': json.dumps(p.get('models', [])),
    }


ALLOWED_BACKENDS = {'openai_compatible', 'anthropic'}


def _validate_preset_input(data):
    """Validate and normalise an incoming preset payload.

    Returns a (record, models_list) tuple suitable for KV insert/update.
    Raises admin.ArgValidationException on invalid input.
    """
    from validators import validate_string, validate_url, validate_choice, validate_key, ValidationError
    try:
        preset_id = validate_key(data.get('preset_id', ''), 'preset_id')
        label = validate_string(data.get('label', '') or preset_id, 'label', max_len=100)
        backend = validate_choice(
            data.get('backend', 'openai_compatible'), 'backend',
            list(ALLOWED_BACKENDS), default='openai_compatible')
        url = data.get('url', '') or ''
        if url:
            url = validate_url(url, 'url')
        models_raw = data.get('models', '')
        if isinstance(models_raw, str):
            # Comma- or newline-separated input from a UI form.
            models = [m.strip() for m in models_raw.replace('\n', ',').split(',') if m.strip()]
        elif isinstance(models_raw, list):
            models = [str(m).strip() for m in models_raw if str(m).strip()]
        else:
            models = []
        # Cap models list to prevent abuse — 200 is way more than any provider ships.
        models = models[:200]
        default_model = data.get('model', '') or (models[0] if models else '')
    except ValidationError as ve:
        raise admin.ArgValidationException(str(ve))

    return {
        '_key': preset_id,
        'preset_id': preset_id,
        'label': label,
        'backend': backend,
        'url': url,
        'model': default_model,
        'models_json': json.dumps(models),
    }, models


class MCPProviderPresetsHandler(MCPBaseHandler):

    def setup(self):
        for arg in ('output_mode', 'preset_id', 'label', 'backend', 'url', 'model', 'models'):
            self.supportedArgs.addOptArg(arg)

    def _arg(self, name, default=''):
        return (self.callerArgs.data.get(name, [default]) or [default])[0] or default

    def _load_from_kv(self):
        """Try to read the KV-backed presets. Returns (presets, source_label).
        On any failure, falls back to BUILT_IN_PRESETS — the UI still loads."""
        try:
            service = self._get_splunk_service()
            kv = KVStoreClient(service, COLLECTION)
        except Exception as e:
            logger.info("provider_presets KV unavailable, using built-in: %s", e)
            return list(BUILT_IN_PRESETS), 'builtin'

        try:
            records = kv.query(query={}, limit=200)
        except KVStoreError as e:
            logger.warning("provider_presets KV query failed: %s", e)
            return list(BUILT_IN_PRESETS), 'builtin'

        if not records:
            # First run on this install — seed from built-ins so admins can edit.
            seeded = 0
            for p in BUILT_IN_PRESETS:
                try:
                    kv.insert(_preset_to_record(p))
                    seeded += 1
                except Exception as e:
                    logger.warning("provider_presets seed failed for %s: %s", p['id'], e)
                    break
            logger.info("provider_presets seeded %d built-in records", seeded)
            return list(BUILT_IN_PRESETS), 'seeded' if seeded else 'builtin'

        return [_record_to_preset(r) for r in records], 'kv'

    def handleList(self, confInfo):
        try:
            presets, source = self._load_from_kv()
            payload = json.dumps(presets)
            confInfo['presets'].append('presets_json', payload)
            confInfo['presets'].append('json', payload)
            confInfo['presets'].append('count', str(len(presets)))
            confInfo['presets'].append('source', source)
        except Exception as e:
            logger.exception("provider presets handler crashed")
            try:
                payload = json.dumps(BUILT_IN_PRESETS)
                confInfo['presets'].append('presets_json', payload)
                confInfo['presets'].append('json', payload)
                confInfo['presets'].append('count', str(len(BUILT_IN_PRESETS)))
                confInfo['presets'].append('source', 'builtin_fallback')
            except Exception:
                pass
            confInfo['presets'].append('error', str(e))

    # Issue #18 UI: full CRUD on the KV-backed preset collection.
    # The Manage Presets view (default/data/ui/views/mcp_provider_presets.xml)
    # exercises these via the standard admin/* REST verbs.
    def _kv(self):
        service = self._get_splunk_service()
        return KVStoreClient(service, COLLECTION)

    def _ensure_seeded(self, kv):
        """Lazily seed BUILT_IN_PRESETS so a brand-new install can immediately
        edit / extend the list rather than starting empty."""
        try:
            existing = kv.query(query={}, limit=1)
            if existing:
                return
        except KVStoreError:
            return
        for p in BUILT_IN_PRESETS:
            try:
                kv.insert(_preset_to_record(p))
            except Exception as e:
                logger.warning("preset seed failed for %s: %s", p['id'], e)

    def handleCreate(self, confInfo):
        try:
            data = {k: (v[0] if v else '') for k, v in (self.callerArgs.data or {}).items()}
            record, _ = _validate_preset_input(data)
            kv = self._kv()
            self._ensure_seeded(kv)
            try:
                # Reject duplicate preset_id on create (use edit to overwrite).
                if kv.get_by_id(record['_key']):
                    raise admin.ArgValidationException(
                        f"Preset '{record['_key']}' already exists; use edit to update."
                    )
            except admin.ArgValidationException:
                raise
            except Exception:
                pass  # get_by_id may legitimately fail when record doesn't exist
            kv.insert(record)
            confInfo['result'].append('success', 'true')
            confInfo['result'].append('preset_id', record['preset_id'])
        except admin.ArgValidationException:
            raise
        except Exception as e:
            logger.exception("preset create failed")
            self._handle_error(confInfo, 'preset_create_failed', e)

    def handleEdit(self, confInfo):
        try:
            record_id = self.callerArgs.id or self._arg('preset_id')
            if not record_id:
                raise admin.ArgValidationException("preset_id is required")
            data = {k: (v[0] if v else '') for k, v in (self.callerArgs.data or {}).items()}
            data.setdefault('preset_id', record_id)
            record, _ = _validate_preset_input(data)
            if record['_key'] != record_id:
                # Renaming presets via edit is dangerous (preset_id == _key),
                # so refuse and force the user to delete + recreate explicitly.
                raise admin.ArgValidationException(
                    "preset_id mismatch with URL path; rename via delete + create instead."
                )
            kv = self._kv()
            self._ensure_seeded(kv)
            try:
                kv.update(record_id, record)
            except KVStoreError:
                # Record may not exist yet — fall back to insert so an admin
                # editing a built-in preset that hasn't been seeded yet still works.
                kv.insert(record)
            confInfo['result'].append('success', 'true')
            confInfo['result'].append('preset_id', record_id)
        except admin.ArgValidationException:
            raise
        except Exception as e:
            logger.exception("preset edit failed")
            self._handle_error(confInfo, 'preset_edit_failed', e)

    def handleRemove(self, confInfo):
        try:
            record_id = self.callerArgs.id or self._arg('preset_id')
            if not record_id:
                raise admin.ArgValidationException("preset_id is required")
            kv = self._kv()
            kv.delete(record_id)
            confInfo['result'].append('success', 'true')
            confInfo['result'].append('preset_id', record_id)
        except admin.ArgValidationException:
            raise
        except Exception as e:
            logger.exception("preset remove failed")
            self._handle_error(confInfo, 'preset_remove_failed', e)


admin.init(MCPProviderPresetsHandler, admin.CONTEXT_APP_AND_USER)
