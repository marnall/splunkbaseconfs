"""MCP License Limits Handler"""
import sys, os, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
import splunk.admin as admin
from mcp_base import MCPBaseHandler, KVStoreClient
from usage_tracker import get_daily_query_count, get_concurrent_query_count

logger = logging.getLogger(__name__)

class MCPLicenseLimitsHandler(MCPBaseHandler):

    def setup(self):
        self.supportedArgs.addOptArg('output_mode')

    def handleList(self, confInfo):
        """Get current license limits and usage statistics."""
        try:
            self._check_license()

            limits = self._get_license_limits()
            license_data = self._get_license_data()
            user = getattr(self, 'userName', None) or 'unknown'

            # Get current usage counts
            service = self._get_splunk_service()

            # Provider count
            kv_client = KVStoreClient(service, 'mcp_ai_providers')
            provider_count = len(kv_client.query(limit=200))

            # Template count
            kv_client = KVStoreClient(service, 'mcp_query_templates')
            template_count = len(kv_client.query(limit=200))

            # Query usage
            daily_query_count = get_daily_query_count(user)
            concurrent_query_count = get_concurrent_query_count(user)

            # Build response
            response = {
                'license_type': license_data.get('license_type', 'starter') if license_data else 'starter',
                'limits': limits,
                'usage': {
                    'providers': {
                        'current': provider_count,
                        'max': limits.get('max_providers', 1),
                        'unlimited': limits.get('max_providers', 1) == -1
                    },
                    'templates': {
                        'current': template_count,
                        'max': limits.get('max_templates', 5),
                        'unlimited': limits.get('max_templates', 5) == -1
                    },
                    'daily_queries': {
                        'current': daily_query_count,
                        'max': limits.get('daily_query_limit', -1),
                        'unlimited': limits.get('daily_query_limit', -1) == -1
                    },
                    'concurrent_queries': {
                        'current': concurrent_query_count,
                        'max': limits.get('max_concurrent_queries', 5)
                    }
                }
            }

            confInfo['limits'].append('data', json.dumps(response))

        except Exception as e:
            logger.exception("Failed to get license limits")
            self._handle_error(confInfo, 'error', str(e))

admin.init(MCPLicenseLimitsHandler, admin.CONTEXT_APP_AND_USER)
