"""MCP Providers Handler"""
import sys, os, json, time, uuid, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
import splunk.admin as admin
from mcp_base import MCPBaseHandler, KVStoreClient
from validators import validate_string, validate_url, validate_choice, ValidationError

logger = logging.getLogger(__name__)

class MCPProvidersHandler(MCPBaseHandler):

    def setup(self):
        # `project / location / vertexai` are v4 additions used only by the
        # Google provider path. They are persisted to KV verbatim and consumed
        # by bin/lib/agentic/providers.py::build_model when constructing a
        # GoogleModel (Gemini API vs Vertex AI). Other provider types ignore
        # them.
        for arg in ('provider_name', 'provider_type', 'base_url', 'model',
                    'api_key', 'is_default', 'enabled',
                    'project', 'location', 'vertexai',
                    'output_mode'):
            self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        try:
            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_ai_providers')
            records = kv_client.query(limit=200)

            # Auto-migrate old providers that have api_key but no credential_key
            for record in records:
                try:
                    has_api_key = record.get('api_key')
                    has_credential_key = record.get('credential_key')
                    if has_api_key and not has_credential_key:
                        provider_id = record.get('provider_id', '')
                        name = record.get('name', provider_id)
                        credential_key = 'mcp_provider_%s' % provider_id.replace('-', '_')
                        stored = self._store_encrypted_credential(credential_key, has_api_key)
                        if stored:
                            record['credential_key'] = credential_key
                            record.pop('api_key', None)
                            kv_client.update(record['_key'], record)
                            logger.info(f"Migrated provider {name} credentials to storage/passwords")
                except Exception:
                    logger.warning(f"Failed to migrate provider {record.get('name', 'unknown')}, will retry on next list")

            # Allow-list: never serialize api_key — even if migration on this
            # request did not run for some record, we must not leak the secret.
            ALLOWED_FIELDS = {
                '_key', 'provider_id', 'name', 'provider_type', 'base_url',
                'model', 'credential_key', 'is_default', 'enabled',
                'created_at', 'updated_at',
                # v4 Google fields (only populated on google provider records)
                'project', 'location', 'vertexai',
            }
            for record in records:
                key = record.get('_key', '')
                entry = confInfo[key]
                for field, value in record.items():
                    if field not in ALLOWED_FIELDS:
                        continue
                    entry.append(field, str(value) if value is not None else '')
        except Exception as e:
            logger.exception("Failed to list providers")
            confInfo['error'].append('message', str(e))

    def handleCreate(self, confInfo):
        try:
            self._check_license()
            self._check_provider_limit()

            name = self.callerArgs.data.get('provider_name', [None])[0]
            provider_type = self.callerArgs.data.get('provider_type', ['openai_compatible'])[0]
            base_url = self.callerArgs.data.get('base_url', [''])[0] or ''
            model = self.callerArgs.data.get('model', [''])[0] or ''
            api_key = self.callerArgs.data.get('api_key', [''])[0] or ''
            is_default = self.callerArgs.data.get('is_default', ['false'])[0]
            is_default_bool = self._normalize_bool(is_default)
            # `enabled` defaults to True so the existing UI (which never sends
            # this field) keeps creating active providers, but we read it when
            # supplied so a future UI / API client can create a disabled one.
            enabled_raw = self.callerArgs.data.get('enabled', ['true'])[0]
            enabled_bool = self._normalize_bool(enabled_raw)
            # v4 Google fields. Empty strings on non-Google providers are
            # benign — the Model factory in agentic.providers ignores them.
            project = self.callerArgs.data.get('project', [''])[0] or ''
            location = self.callerArgs.data.get('location', [''])[0] or ''
            vertexai_raw = self.callerArgs.data.get('vertexai', [''])[0]
            # vertexai is a 3-state in KV: True / False / unset. We persist
            # None when the admin didn't send it so the GoogleModel backend
            # auto-detect (Gemini API vs Vertex) still runs.
            vertexai_val = self._normalize_bool(vertexai_raw) if vertexai_raw not in ('', None) else None

            try:
                name = validate_string(name, 'provider_name', max_len=100)
                provider_type = validate_choice(
                    provider_type, 'provider_type',
                    ['openai_compatible', 'anthropic', 'google'],
                )
                if base_url:
                    base_url = validate_url(base_url, 'base_url')
                if model:
                    model = validate_string(model, 'model', max_len=200)
                if project:
                    project = validate_string(project, 'project', max_len=200)
                if location:
                    location = validate_string(location, 'location', max_len=100)
            except ValidationError as ve:
                raise admin.ArgValidationException(str(ve))

            if is_default_bool:
                self._clear_default_providers()

            provider_id = str(uuid.uuid4())
            now = int(time.time())

            # Store API key in storage/passwords (encrypted)
            credential_key = 'mcp_provider_%s' % provider_id.replace('-', '_')
            if api_key:
                self._store_encrypted_credential(credential_key, api_key)

            record = {
                'provider_id': provider_id,
                'name': name,
                'provider_type': provider_type,
                'base_url': base_url,
                'model': model,
                'credential_key': credential_key,
                'is_default': is_default_bool,
                'enabled': enabled_bool,
                'created_at': now,
                'updated_at': now,
            }
            # Only persist Google-specific fields when the provider_type is
            # 'google' AND the admin actually supplied them. Empty values are
            # dropped so the KV row stays compact for other backends.
            if provider_type == 'google':
                if project:
                    record['project'] = project
                if location:
                    record['location'] = location
                if vertexai_val is not None:
                    record['vertexai'] = vertexai_val

            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_ai_providers')
            record_key = kv_client.insert(record)

            if is_default_bool:
                self._update_default_provider_id(provider_id)

            confInfo['result'].append('success', 'true')
            confInfo['result'].append('provider_id', provider_id)
            confInfo['result'].append('_key', record_key)

        except admin.ArgValidationException:
            raise
        except Exception as e:
            logger.exception(f"{self._log_prefix()} Failed to create provider")
            self._handle_error(confInfo, 'error', str(e))

    def handleEdit(self, confInfo):
        try:
            record_id = self.callerArgs.id
            if not record_id:
                raise admin.ArgValidationException("Provider ID is required")

            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_ai_providers')
            existing = kv_client.get_by_id(record_id)
            if not existing:
                raise admin.ArgValidationException(f"Provider {record_id} not found")

            for field in ['provider_name', 'provider_type', 'base_url', 'model',
                          'is_default', 'enabled',
                          'project', 'location', 'vertexai']:
                val = self.callerArgs.data.get(field, [None])[0]
                if val is not None:
                    store_field = 'name' if field == 'provider_name' else field
                    if field == 'is_default':
                        val = self._normalize_bool(val)
                        if val:
                            self._clear_default_providers()
                    elif field == 'enabled':
                        val = self._normalize_bool(val)
                    elif field == 'vertexai':
                        # Allow clearing vertexai with empty string (so the
                        # GoogleModel auto-detect can take over again).
                        val = self._normalize_bool(val) if val != '' else None
                    else:
                        try:
                            if field == 'provider_name':
                                val = validate_string(val, 'provider_name', max_len=100)
                            elif field == 'provider_type':
                                val = validate_choice(
                                    val, 'provider_type',
                                    ['openai_compatible', 'anthropic', 'google'],
                                )
                            elif field == 'base_url' and val:
                                val = validate_url(val, 'base_url')
                            elif field == 'model':
                                val = validate_string(val, 'model', min_len=0, max_len=200)
                            elif field == 'project' and val:
                                val = validate_string(val, 'project', max_len=200)
                            elif field == 'location' and val:
                                val = validate_string(val, 'location', max_len=100)
                        except ValidationError as ve:
                            raise admin.ArgValidationException(str(ve))
                    # Skip persistence when vertexai was cleared back to None
                    # (KV doesn't store None — just drop the key).
                    if field == 'vertexai' and val is None:
                        existing.pop('vertexai', None)
                    else:
                        existing[store_field] = val

            # Handle API key update via storage/passwords
            api_key = self.callerArgs.data.get('api_key', [None])[0]
            if api_key:
                credential_key = existing.get('credential_key', '')
                if not credential_key:
                    credential_key = 'mcp_provider_%s' % existing.get('provider_id', record_id).replace('-', '_')
                    existing['credential_key'] = credential_key
                self._store_encrypted_credential(credential_key, api_key)

            existing['updated_at'] = int(time.time())
            kv_client.update(record_id, existing)

            if existing.get('is_default'):
                self._update_default_provider_id(existing.get('provider_id', ''))

            confInfo['result'].append('success', 'true')
            confInfo['result'].append('message', 'Provider updated successfully')

        except admin.ArgValidationException:
            raise
        except Exception as e:
            logger.exception(f"{self._log_prefix()} Failed to update provider")
            self._handle_error(confInfo, 'error', str(e))

    def handleRemove(self, confInfo):
        try:
            record_id = self.callerArgs.id
            if not record_id:
                raise admin.ArgValidationException("Provider ID is required")

            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_ai_providers')

            # Get the record first to find the credential_key
            existing = kv_client.get_by_id(record_id)
            if existing:
                credential_key = existing.get('credential_key', '')
                if credential_key:
                    self._delete_encrypted_credential(credential_key)

            kv_client.delete(record_id)

            confInfo['result'].append('success', 'true')
            confInfo['result'].append('message', 'Provider deleted successfully')

        except admin.ArgValidationException:
            raise
        except Exception as e:
            logger.exception(f"{self._log_prefix()} Failed to delete provider")
            self._handle_error(confInfo, 'error', str(e))

admin.init(MCPProvidersHandler, admin.CONTEXT_APP_AND_USER)
