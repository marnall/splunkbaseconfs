import time
import json
import urllib.parse
import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication



















APP = "dv_ai_assistant"
COLL = "dv_chat_history"
KV_BASE = f"/servicesNS/nobody/{APP}/storage/collections/data/{COLL}"


class AIHistoryHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(AIHistoryHandler, self).__init__()

    
    @staticmethod
    def _json(obj, status=200):
        return {'payload': json.dumps(obj), 'status': status,
                'headers': {'Content-Type': 'application/json'}}

    @staticmethod
    def _form(req):
        d = {}
        for kv in req.get('form', []):
            d[kv[0]] = kv[1]
        if not d:
            try:
                p = req.get('payload')
                if p:
                    d = json.loads(p)
            except Exception:
                d = {}
        return d

    @staticmethod
    def _query(req):
        d = {}
        for kv in req.get('query', []):
            d[kv[0]] = kv[1]
        return d

    def _kv_find(self, sys_key, query):
        url = KV_BASE + '?query=' + urllib.parse.quote(json.dumps(query))
        _, c = rest.simpleRequest(url, sessionKey=sys_key, method='GET')
        return json.loads(c)

    
    def handle(self, in_string):
        try:
            req = json.loads(in_string)
            method = req.get('method', 'GET').upper()

            
            user = (req.get('session', {}) or {}).get('user', '') or ''
            
            sys_key = req.get('system_authtoken') or (req.get('session', {}) or {}).get('authtoken', '')

            if not user or user == 'nobody':
                return self._json({"error": "no authenticated user"}, 401)

            if method == 'GET':
                return self._list(sys_key, user)
            if method == 'POST':
                return self._save(sys_key, user, req)
            if method == 'DELETE':
                return self._delete(sys_key, user, req)
            return self._json({"error": "method not allowed"}, 405)
        except Exception as e:
            return self._json({"error": "unhandled", "details": str(e)}, 500)

    
    def _list(self, sys_key, user):
        try:
            rows = self._kv_find(sys_key, {"user": user})
        except Exception as e:
            return self._json({"error": "kv read failed", "details": str(e)}, 500)
        try:
            rows.sort(key=lambda r: str(r.get('timestamp', '')), reverse=True)
        except Exception:
            pass
        out = [{
            "_key": r.get('_key', ''),
            "session_id": r.get('session_id', ''),
            "title": r.get('title', ''),
            "messages": r.get('messages', '[]'),
            "timestamp": r.get('timestamp', '')
        } for r in rows]
        return self._json(out, 200)

    
    def _save(self, sys_key, user, req):
        f = self._form(req)
        session_id = str(f.get('session_id', '')).strip()
        if not session_id:
            return self._json({"error": "session_id required"}, 400)

        record = {
            "user": user,                                  
            "session_id": session_id,
            "title": str(f.get('title', ''))[:200],
            "messages": f.get('messages', '[]'),
            "timestamp": str(f.get('timestamp', '') or int(time.time() * 1000))
        }

        
        existing_key = None
        try:
            found = self._kv_find(sys_key, {"user": user, "session_id": session_id})
            if found:
                existing_key = found[0].get('_key')
        except Exception:
            existing_key = None

        try:
            if existing_key:
                rest.simpleRequest(f"{KV_BASE}/{existing_key}", sessionKey=sys_key,
                                   jsonargs=json.dumps(record), method='POST')
                key = existing_key
            else:
                _, c = rest.simpleRequest(KV_BASE, sessionKey=sys_key,
                                          jsonargs=json.dumps(record), method='POST')
                key = json.loads(c).get('_key', '')
        except Exception as e:
            return self._json({"error": "kv write failed", "details": str(e)}, 500)

        return self._json({"_key": key, "session_id": session_id}, 200)

    
    def _delete(self, sys_key, user, req):
        q = self._query(req)
        target = q.get('session_id', '') or q.get('_key', '')

        
        if q.get('all', '') in ('1', 'true', 'yes') or target == '__ALL__':
            try:
                rows = self._kv_find(sys_key, {"user": user})
                for r in rows:
                    k = r.get('_key')
                    if k:
                        rest.simpleRequest(f"{KV_BASE}/{k}", sessionKey=sys_key, method='DELETE')
            except Exception as e:
                return self._json({"error": "kv delete failed", "details": str(e)}, 500)
            return self._json({"status": "cleared"}, 200)

        if not target:
            return self._json({"error": "session_id or _key required"}, 400)

        
        try:
            found = self._kv_find(sys_key, {"user": user, "session_id": target})
            if not found:
                found = self._kv_find(sys_key, {"user": user, "_key": target})
            for r in found:
                k = r.get('_key')
                if k:
                    rest.simpleRequest(f"{KV_BASE}/{k}", sessionKey=sys_key, method='DELETE')
        except Exception as e:
            return self._json({"error": "kv delete failed", "details": str(e)}, 500)

        return self._json({"status": "deleted"}, 200)
