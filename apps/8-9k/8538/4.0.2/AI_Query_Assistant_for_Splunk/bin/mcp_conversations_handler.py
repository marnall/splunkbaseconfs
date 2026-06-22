"""MCP Conversations Handler (v4.0.0).

REST endpoint that backs the multi-turn UI added in task #5. It exposes the
KV-store-backed conversation history that the agentic ConversationStore writes
to (see bin/lib/agentic/conversation.py).

Endpoints (under the existing admin/<app>/ namespace):

  GET  /servicesNS/<user>/<app>/mcp_conversations                       list threads for current user
  GET  /servicesNS/<user>/<app>/mcp_conversations?thread_id=<id>        list messages in a single thread
  DELETE /servicesNS/<user>/<app>/mcp_conversations/<thread_id>          delete one thread (and its messages)

Authorization: regular users always see only their own threads. Callers with
the admin_all_objects capability may pass ``scope=all`` on the list path to
see every user's threads (mirrors mcp_history_handler.py).

The handler intentionally does NOT mutate threads on write — that's the
agentic pipeline's job (via SplunkKVConversationStore). This module is
read-mostly, with delete as the one mutation.
"""
import sys, os, json, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))
import splunk.admin as admin
from mcp_base import MCPBaseHandler, KVStoreClient
from validators import validate_int, validate_string, ValidationError

logger = logging.getLogger(__name__)

_THREADS_COLLECTION = 'mcp_conversation_threads'
_MESSAGES_COLLECTION = 'mcp_conversation_messages'


class MCPConversationsHandler(MCPBaseHandler):

    def setup(self):
        for arg in ('thread_id', 'limit', 'offset', 'scope', 'output_mode'):
            self.supportedArgs.addOptArg(arg)

    def _can_view_all(self):
        try:
            caps = getattr(self, 'userCapabilities', None) or {}
            return bool(caps.get('admin_all_objects'))
        except Exception:
            return False

    # ------------------------------------------------------------------
    # GET  → list threads or list messages-in-thread, depending on params
    # ------------------------------------------------------------------

    def handleList(self, confInfo):
        try:
            user = getattr(self, 'userName', None) or 'unknown'
            service = self._get_splunk_service()

            thread_id = (self.callerArgs.data.get('thread_id', [None]) or [None])[0]

            if thread_id:
                self._list_messages_for_thread(confInfo, service, user, thread_id)
            else:
                self._list_threads(confInfo, service, user)

        except admin.ArgValidationException:
            raise
        except Exception as e:
            logger.exception("Failed to list conversations")
            confInfo['conversations'].append('error', str(e))

    def _list_threads(self, confInfo, service, user):
        try:
            limit = validate_int(
                self.callerArgs.data.get('limit', [50])[0],
                'limit', min_val=1, max_val=500, default=50,
            )
            offset = validate_int(
                self.callerArgs.data.get('offset', [0])[0],
                'offset', min_val=0, max_val=100000, default=0,
            )
        except ValidationError as ve:
            raise admin.ArgValidationException(str(ve))

        scope = (self.callerArgs.data.get('scope', ['mine']) or ['mine'])[0]
        kv = KVStoreClient(service, _THREADS_COLLECTION)

        if scope == 'all' and self._can_view_all():
            kv_query = None
            actual_scope = 'all'
        else:
            kv_query = {'user': user}
            actual_scope = 'mine'

        records = kv.query(kv_query, limit=limit, skip=offset) or []
        # Sort newest first — KV doesn't guarantee an order, and ConversationStore
        # writes `last_activity` epoch seconds on every turn.
        records.sort(key=lambda r: r.get('last_activity', 0), reverse=True)

        # Trim payload to UI-relevant fields only; keep raw size small.
        slim = [
            {
                'thread_id': r.get('thread_id', ''),
                'user': r.get('user', ''),
                'title': r.get('title', '') or _derive_title(r),
                'last_activity': r.get('last_activity', 0),
                'message_count': int(r.get('message_count', 0) or 0),
                'archived': bool(r.get('archived', False)),
                'created_at': r.get('created_at', 0),
            }
            for r in records
        ]

        confInfo['conversations'].append('threads', json.dumps(slim))
        confInfo['conversations'].append('count', str(len(slim)))
        confInfo['conversations'].append('scope', actual_scope)

    def _list_messages_for_thread(self, confInfo, service, user, thread_id):
        try:
            thread_id = validate_string(thread_id, 'thread_id', max_len=200)
        except ValidationError as ve:
            raise admin.ArgValidationException(str(ve))

        # Cap how many messages we hand back so a runaway thread can't OOM the
        # browser. The agent's own conversation store is already trimmed by
        # AgentLimits.max_steps; this is a defense-in-depth UI cap.
        try:
            limit = validate_int(
                self.callerArgs.data.get('limit', [200])[0],
                'limit', min_val=1, max_val=2000, default=200,
            )
        except ValidationError as ve:
            raise admin.ArgValidationException(str(ve))

        msgs_kv = KVStoreClient(service, _MESSAGES_COLLECTION)
        # Filter by both user AND thread_id so a stolen thread_id can't expose
        # someone else's history.
        rows = msgs_kv.query({'user': user, 'thread_id': thread_id}, limit=limit) or []
        rows.sort(key=lambda r: int(r.get('seq', 0) or 0))

        slim = [
            {
                'seq': int(r.get('seq', 0) or 0),
                'role': r.get('role', ''),
                'content': r.get('content', ''),
                'created_at': r.get('created_at', 0),
            }
            for r in rows
        ]

        confInfo['conversations'].append('thread_id', thread_id)
        confInfo['conversations'].append('messages', json.dumps(slim))
        confInfo['conversations'].append('count', str(len(slim)))

    # ------------------------------------------------------------------
    # DELETE → drop a thread and all of its messages
    # ------------------------------------------------------------------

    def handleRemove(self, confInfo):
        try:
            thread_id = self.callerArgs.id  # /mcp_conversations/<thread_id>
            if not thread_id:
                raise admin.ArgValidationException("thread_id is required")
            try:
                thread_id = validate_string(thread_id, 'thread_id', max_len=200)
            except ValidationError as ve:
                raise admin.ArgValidationException(str(ve))

            user = getattr(self, 'userName', None) or 'unknown'
            service = self._get_splunk_service()

            threads_kv = KVStoreClient(service, _THREADS_COLLECTION)
            msgs_kv = KVStoreClient(service, _MESSAGES_COLLECTION)

            # Ownership check: only the owning user (or admin) may delete.
            existing = threads_kv.query(
                {'thread_id': thread_id}, limit=1,
            ) or []
            if not existing:
                confInfo['result'].append('success', 'true')
                confInfo['result'].append('message', 'Thread already absent')
                return
            owner = existing[0].get('user', '')
            if owner and owner != user and not self._can_view_all():
                raise admin.AdminManagerException(
                    "You do not have permission to delete that thread."
                )

            # Delete messages by thread_id (one row at a time; KVStoreClient
            # has no bulk-delete-by-query API in v3).
            for m in msgs_kv.query({'thread_id': thread_id}, limit=10000) or []:
                key = m.get('_key')
                if key:
                    try:
                        msgs_kv.delete(key)
                    except Exception as e:
                        logger.warning(f"Failed to delete message {key}: {e}")

            # Delete the thread metadata row.
            for r in existing:
                key = r.get('_key')
                if key:
                    threads_kv.delete(key)

            confInfo['result'].append('success', 'true')
            confInfo['result'].append('thread_id', thread_id)

        except admin.ArgValidationException:
            raise
        except admin.AdminManagerException:
            raise
        except Exception as e:
            logger.exception("Failed to delete conversation thread")
            confInfo['result'].append('error', str(e))


def _derive_title(record):
    """Fallback title for threads where the store didn't populate one.

    We use a short prefix of the first user message if available, otherwise
    the thread_id. Computed here so the UI doesn't have to think about it.
    """
    title = record.get('first_message_preview') or record.get('thread_id', '')
    if isinstance(title, str) and len(title) > 60:
        title = title[:57] + '...'
    return title or 'Untitled conversation'


admin.init(MCPConversationsHandler, admin.CONTEXT_APP_AND_USER)
