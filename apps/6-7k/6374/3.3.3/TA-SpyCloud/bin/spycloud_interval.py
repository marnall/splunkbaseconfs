import json
from urllib.parse import parse_qs, quote
import splunk.rest
import splunk

APP = "TA-SpyCloud"
KIND_DEFAULT = "spycloud_watchlist"
STANZA_DEFAULT = "SpyCloud_Watchlist"

def _first(val):
    return val[0] if isinstance(val, list) and val else val

class Interval(splunk.rest.BaseRestHandler):
    def _session_key(self):
        return getattr(self, "sessionKey", None) or self.getSessionKey()

    def _json(self, obj, status=200):
        self.response.setHeader("content-type", "application/json")
        try:
            self.response.setStatus(status)
        except Exception:
            pass
        self.response.write(json.dumps(obj))

    def _get_params(self):
        # read from query
        q = self.request.get("query") or {}
        if isinstance(q, str):
            q = {k: _first(v) for k, v in parse_qs(q).items()}
        else:
            q = {k: _first(v) for k, v in q.items()}
        # read from payload
        payload = self.request.get("payload") or ""
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="ignore")
        form = {k: _first(v) for k, v in parse_qs(payload).items()}

        kind = form.get("kind", q.get("kind", KIND_DEFAULT))
        stanza = form.get("stanza", q.get("stanza", STANZA_DEFAULT))
        interval_value = form.get("interval")

        return kind, stanza, interval_value

    def _path(self, kind, stanza):
        kind_q = quote(kind, safe="")
        stanza_q = quote(stanza, safe="")
        return f"/servicesNS/nobody/{APP}/data/inputs/{kind_q}/{stanza_q}"

    def _read(self, kind, stanza):
        resp, body = splunk.rest.simpleRequest(
            self._path(kind, stanza),
            sessionKey=self._session_key(),
            method="GET",
            getargs={"output_mode": "json"},
            raiseAllErrors=True,
        )
        data = json.loads(body)
        return data["entry"][0]["content"]

    def _set(self, kind, stanza, interval_value):
        splunk.rest.simpleRequest(
            self._path(kind, stanza),
            sessionKey=self._session_key(),
            method="POST",
            postargs={"interval": interval_value, "output_mode": "json"},
            raiseAllErrors=True,
        )

    def handle_GET(self):
        try:
            kind, stanza, _ = self._get_params()
            content = self._read(kind, stanza)
            self._json({"ok": True, "kind": kind, "stanza": stanza, "content": content})
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, status=500)

    def handle_POST(self):
        try:
            kind, stanza, interval_value = self._get_params()
            if not interval_value:
                self._json({"ok": False, "error": "missing interval"}, status=400)
                return
            self._set(kind, stanza, interval_value)
            content = self._read(kind, stanza)
            self._json({"ok": True, "kind": kind, "stanza": stanza, "content": content})
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, status=500)
