"""
lookup_ax_config_handler.py
Managed CSV list + schema CRUD (KV Store: lookup_ax_schemas)
"""
import json
import urllib.parse
import logging

import splunk.rest

logger = logging.getLogger(__name__)

APP = 'lookup-editor-ax'
KV_BASE = f'/servicesNS/nobody/{APP}/storage/collections/data'
COLL = 'lookup_ax_schemas'


def _kv_path(key=None):
    path = f'{KV_BASE}/{COLL}'
    if key:
        path += '/' + urllib.parse.quote(str(key), safe='')
    return path + '?output_mode=json'


def _kv_req(path, method='GET', data=None, session_key=''):
    kwargs = dict(sessionKey=session_key, method=method, raiseAllErrors=True)
    if data is not None:
        # ensure_ascii=True (default) — \uXXXX escaping keeps it ASCII-safe (avoids Latin-1 encoding errors)
        kwargs['jsonargs'] = json.dumps(data)
    _, content = splunk.rest.simpleRequest(path, **kwargs)
    raw = content.decode('utf-8') if isinstance(content, bytes) else content
    return json.loads(raw) if raw.strip() else {}


def _user_has_capability(session_key, capability):
    """Check whether the current session user holds the given capability.
    Note: session_key must be the user's own token (calling with systemAuth returns the system user's capabilities).
    """
    try:
        _, content = splunk.rest.simpleRequest(
            '/services/authentication/current-context?output_mode=json',
            sessionKey=session_key, method='GET', raiseAllErrors=True
        )
        raw = content.decode('utf-8') if isinstance(content, bytes) else content
        data = json.loads(raw)
        entries = data.get('entry', [])
        if not entries:
            return False
        caps = entries[0].get('content', {}).get('capabilities', [])
        return capability in caps
    except Exception:
        return False


class LookupAxConfigHandler(splunk.rest.BaseRestHandler):

    def _session_key(self):
        # For operations that need elevated access such as KV Store (prefer systemAuth)
        return (self.request.get('systemAuth') or self.request.get('session_key', ''))

    def _user_session_key(self):
        """For capability checks — the calling user's own token.
        self.sessionKey is set by BaseRestHandler to the user's auth token.
        self.request['session_key'] may be empty, so prefer self.sessionKey.
        self.request['systemAuth'] is the system token, so it cannot be used for capability checks.
        """
        return getattr(self, 'sessionKey', '') or self.request.get('session_key', '')

    def _qp(self, key, default=''):
        query = self.request.get('query') or {}
        val = query.get(key, default)
        return val[0] if isinstance(val, list) else (val if val is not None else default)

    def _send_json(self, obj):
        self.response.setStatus(200)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps(obj))

    def handle_GET(self):
        sk = self._session_key()
        key = self._qp('key')
        try:
            if key:
                rec = _kv_req(_kv_path(key), method='GET', session_key=sk)
                records = [rec] if isinstance(rec, dict) and '_key' in rec else (rec if isinstance(rec, list) else [])
            else:
                records = _kv_req(_kv_path(), method='GET', session_key=sk)
                if isinstance(records, dict):
                    records = [records]
                if not isinstance(records, list):
                    records = []

            result = [{
                'key':          r.get('_key', ''),
                'app':          r.get('app', ''),
                'filename':     r.get('filename', ''),
                'label':        r.get('label', ''),
                'columns':      r.get('columns', '[]'),
                'column_types': r.get('column_types', '{}'),
                'max_backups':  r.get('max_backups', '10'),
            } for r in records]
            # Include permission info so the client can decide whether to switch the Manager UI to view-only.
            # Capability checks must use the user's own token, not the system token, to be accurate
            self._send_json({
                'status': 'ok',
                'data': result,
                'hasAdminCap': _user_has_capability(self._user_session_key(), 'lookup_ax_admin'),
            })
        except Exception as e:
            logger.exception('Config GET error')
            self._send_json({'status': 'error', 'message': str(e)})

    def handle_POST(self):
        sk = self._session_key()
        # Create/update/delete require lookup_ax_admin — validate with the user token to prevent system-token bypass
        if not _user_has_capability(self._user_session_key(), 'lookup_ax_admin'):
            self.response.setStatus(403)
            self._send_json({
                'status': 'error',
                'code':   'missing_capability',
                'message': 'lookup_ax_admin capability required to modify schemas',
            })
            return
        raw = self.request.get('payload', '') or ''
        params = urllib.parse.parse_qs(raw)

        def g(k, d=''):
            vals = params.get(k, [d])
            return vals[0] if vals else d

        action = g('action', 'upsert')
        key = g('key', '')

        try:
            if action == 'delete':
                if not key:
                    self._send_json({'status': 'error', 'message': 'key required for delete'})
                    return
                _kv_req(_kv_path(key), method='DELETE', session_key=sk)
                self._send_json({'status': 'deleted'})
                return

            app = g('app')
            filename = g('filename')
            if not app or not filename:
                self._send_json({'status': 'error', 'message': 'app and filename required'})
                return

            record_key = key or f'{app}__{filename}'
            record = {
                '_key':         record_key,
                'app':          app,
                'filename':     filename,
                'label':        g('label', filename),
                'columns':      g('columns', '[]'),
                # Per-column type overlay (JSON map {name: {"type": "number"}}). Columns without an
                # entry default to string. Stored as-is; missing on legacy records → '{}'.
                'column_types': g('column_types', '{}'),
                'max_backups':  g('max_backups', '10'),
            }
            # Update if the key already exists (include key in URL), otherwise create
            try:
                _kv_req(_kv_path(record_key), method='GET', session_key=sk)
                exists = True
            except Exception:
                exists = False
            if exists:
                _kv_req(_kv_path(record_key), method='POST', data=record, session_key=sk)
            else:
                _kv_req(_kv_path(), method='POST', data=record, session_key=sk)
            self._send_json({'status': 'ok', 'key': record['_key']})
        except Exception as e:
            logger.exception('Config POST error')
            self._send_json({'status': 'error', 'message': str(e)})
