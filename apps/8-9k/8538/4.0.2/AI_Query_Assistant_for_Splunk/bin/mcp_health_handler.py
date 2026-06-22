"""MCP Health Handler"""
import sys, os, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
import splunk.admin as admin
from mcp_base import MCPBaseHandler, KVStoreClient
from ai_providers import create_adapter
from integration_client import IntegrationClient

logger = logging.getLogger(__name__)

class MCPHealthHandler(MCPBaseHandler):

    def setup(self):
        self.supportedArgs.addOptArg('output_mode')

    def handleList(self, confInfo):
        try:
            config = self._get_config()

            ai_status = 'unknown'
            try:
                provider = self._get_default_provider()
                if provider:
                    adapter = create_adapter(provider)
                    test_result = adapter.test_connection()
                    ai_status = 'ok' if test_result['success'] else f"error: {test_result['message']}"
                else:
                    ai_status = 'error: no default provider configured'
            except Exception as e:
                ai_status = f'error: {str(e)}'

            integration_status = 'disabled'
            if config.get('integration', {}).get('enabled', 'false').lower() == 'true':
                try:
                    ic = IntegrationClient(config['integration'], session_key=self.getSessionKey())
                    test_result = ic.test_connection()
                    integration_status = 'ok' if test_result['success'] else f"error: {test_result['message']}"
                except Exception as e:
                    integration_status = f'error: {str(e)}'

            kv_status = 'unknown'
            try:
                service = self._get_splunk_service()
                kv_client = KVStoreClient(service, 'mcp_query_history')
                kv_client.query(limit=1)
                kv_status = 'ok'
            except Exception as e:
                kv_status = f'error: {str(e)}'

            # File-integrity check: compares on-disk hashes to the
            # shipped default/manifest.sha256 (built into the .tar.gz at
            # release time). A mismatch means someone tampered with the
            # app — log + report degraded but don't block (could be a
            # legitimate hot patch from support).
            integrity = {'ok': True}
            try:
                from integrity_checker import verify_manifest
                integrity = verify_manifest()
            except Exception as e:
                integrity = {'ok': True, 'warning': f'check_failed: {e}'}

            integrity_ok = integrity.get('ok', True)
            health = {
                'ai': ai_status,
                'integration': integration_status,
                'kv_store': kv_status,
                'integrity': integrity_ok,
                'integrity_detail': {
                    'mismatched_count': len(integrity.get('mismatched') or []),
                    'missing_count':    len(integrity.get('missing')    or []),
                    'total':            integrity.get('total', 0),
                    'warning':          integrity.get('warning', ''),
                    'sample_mismatched': (integrity.get('mismatched') or [])[:5],
                },
                'overall': (
                    'ok' if ai_status == 'ok' and kv_status == 'ok' and integrity_ok
                    else 'degraded'
                ),
            }

            confInfo['health'].append('status', json.dumps(health))

        except Exception as e:
            logger.exception("Health check failed")
            confInfo['health'].append('error', str(e))

admin.init(MCPHealthHandler, admin.CONTEXT_APP_AND_USER)
