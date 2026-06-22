"""REST handler that tests a provider configuration without persisting it.

The Setup / Provider page calls this endpoint when the user clicks
"Test Connection" in the provider editor. The previous build referenced this
endpoint from `web.conf` and from `mcp_providers.js` but never registered a
handler, so every click returned a 404 wrapped as an opaque "Test failed".

POST /servicesNS/nobody/AI_Query_Assistant_for_Splunk/admin/mcp_provider_test
    provider_type   = openai_compatible | anthropic   (required)
    base_url        = HTTP(S) URL                     (required)
    model           = string                          (required)
    credential_key  = name in storage/passwords       (preferred)
    api_key         = direct secret                   (fallback)

Returns confInfo['result'] entries:
    success = "true" | "false"
    message = human-readable diagnostic
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import splunk.admin as admin
from mcp_base import MCPBaseHandler
from validators import validate_url, validate_key, ValidationError
from ai_providers import create_adapter

logger = logging.getLogger(__name__)

ALLOWED_PROVIDER_TYPES = {'openai_compatible', 'anthropic'}


class MCPProviderTestHandler(MCPBaseHandler):

    def setup(self):
        for arg in ('provider_type', 'base_url', 'model', 'credential_key', 'api_key'):
            self.supportedArgs.addOptArg(arg)

    def _arg(self, name, default=''):
        return (self.callerArgs.data.get(name, [default]) or [default])[0] or default

    def handleList(self, confInfo):
        # GET → no-op response so the endpoint is discoverable; never returns secrets.
        confInfo['result'].append('endpoint', 'mcp_provider_test')
        confInfo['result'].append('method', 'POST required')

    def handleCreate(self, confInfo):
        # POST /admin/mcp_provider_test (no ID) is dispatched as `create`.
        # The Test Connection button posts without an ID, so route create → edit.
        return self.handleEdit(confInfo)

    def handleEdit(self, confInfo):
        # Issue #8: gate provider-test behind a valid license so unlicensed
        # installs cannot use this endpoint as a free egress channel.
        try:
            self._check_license()
        except admin.AdminManagerException as e:
            self._handle_error(confInfo, 'license_invalid', str(e))
            return

        # Issue #25: rate-limit before any external HTTP call (10 req / 60s
        # per user) so a tight Test Connection click loop cannot DoS upstream
        # AI providers or rack up credit charges.
        if not self._check_rate_limit(max_requests=10, window_seconds=60):
            self._handle_error(
                confInfo, 'rate_limit',
                'Too many provider-test requests. Please wait a minute before retrying.'
            )
            return

        try:
            provider_type = self._arg('provider_type', '').strip().lower() or 'openai_compatible'
            if provider_type not in ALLOWED_PROVIDER_TYPES:
                confInfo['result'].append('success', 'false')
                confInfo['result'].append('message', f"Unsupported provider_type: {provider_type}")
                return

            base_url = self._arg('base_url').strip()
            model = self._arg('model').strip()
            credential_key = self._arg('credential_key').strip()
            api_key = self._arg('api_key').strip()

            if not base_url:
                confInfo['result'].append('success', 'false')
                confInfo['result'].append('message', 'base_url is required')
                return
            try:
                validate_url(base_url, 'base_url')
            except ValidationError as ve:
                confInfo['result'].append('success', 'false')
                confInfo['result'].append('message', str(ve))
                return

            if not model:
                confInfo['result'].append('success', 'false')
                confInfo['result'].append('message', 'model is required')
                return

            # Prefer credential_key from storage/passwords; fall back to direct api_key.
            resolved_key = ''
            if credential_key:
                try:
                    validate_key(credential_key, 'credential_key')
                except ValidationError as ve:
                    confInfo['result'].append('success', 'false')
                    confInfo['result'].append('message', str(ve))
                    return
                resolved_key = self._get_encrypted_credential(credential_key) or ''
            if not resolved_key and api_key:
                resolved_key = api_key

            if not resolved_key:
                confInfo['result'].append('success', 'false')
                confInfo['result'].append(
                    'message',
                    'No API key resolved (credential_key not found and no api_key supplied)'
                )
                return

            cfg = {
                'provider_type': provider_type,
                'base_url': base_url,
                'model': model,
                'api_key': resolved_key,
            }

            try:
                adapter = create_adapter(cfg)
            except Exception as e:
                logger.exception("provider test: adapter init failed")
                confInfo['result'].append('success', 'false')
                confInfo['result'].append('message', f'Adapter init failed: {e}')
                return

            try:
                outcome = adapter.test_connection() or {}
            except Exception as e:
                logger.exception("provider test: connection failed")
                confInfo['result'].append('success', 'false')
                confInfo['result'].append('message', f'Connection error: {e}')
                return

            confInfo['result'].append('success', 'true' if outcome.get('success') else 'false')
            confInfo['result'].append('message', str(outcome.get('message', ''))[:1000])

        except Exception as e:
            logger.exception("provider test handler crashed")
            confInfo['result'].append('success', 'false')
            confInfo['result'].append('message', f'Internal error: {e}')


admin.init(MCPProviderTestHandler, admin.CONTEXT_APP_AND_USER)
