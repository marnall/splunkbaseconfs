"""MCP History Handler.

Lists query history records owned by the current user. Privileged callers
(those with admin_all_objects) may pass ``scope=all`` to view every user's
history. Regular users always see only their own.
"""
import sys, os, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
import splunk.admin as admin
from mcp_base import MCPBaseHandler, KVStoreClient
from validators import validate_int

logger = logging.getLogger(__name__)


class MCPHistoryHandler(MCPBaseHandler):

    def setup(self):
        for arg in ('limit', 'offset', 'scope', 'output_mode'):
            self.supportedArgs.addOptArg(arg)

    def _can_view_all(self):
        try:
            caps = getattr(self, 'userCapabilities', None) or {}
            # userCapabilities is a dict {capability: True/False} in Splunk admin.
            return bool(caps.get('admin_all_objects'))
        except Exception:
            return False

    def handleList(self, confInfo):
        try:
            limit = validate_int(self.callerArgs.data.get('limit', [100])[0],
                                  'limit', min_val=1, max_val=1000, default=100)
            offset = validate_int(self.callerArgs.data.get('offset', [0])[0],
                                   'offset', min_val=0, max_val=100000, default=0)

            scope = (self.callerArgs.data.get('scope', ['mine']) or ['mine'])[0]
            user = getattr(self, 'userName', None) or 'unknown'

            service = self._get_splunk_service()
            kv_client = KVStoreClient(service, 'mcp_query_history')

            kv_query = None
            if scope == 'all' and self._can_view_all():
                kv_query = None  # privileged: see everything
            else:
                kv_query = {'user': user}

            records = kv_client.query(kv_query, limit=limit, skip=offset)

            confInfo['history'].append('records', json.dumps(records))
            confInfo['history'].append('count', str(len(records)))
            confInfo['history'].append('scope', 'all' if kv_query is None else 'mine')

        except Exception as e:
            logger.exception("Failed to list history")
            confInfo['history'].append('error', str(e))


admin.init(MCPHistoryHandler, admin.CONTEXT_APP_AND_USER)
