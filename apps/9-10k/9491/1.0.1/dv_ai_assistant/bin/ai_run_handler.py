"""
REST handler: /servicesNS/<user>/dv_ai_assistant/admin/ai_run

Executes a READ-ONLY SPL search (typically one the assistant generated) and
returns the rows. The guardrail is RE-CHECKED here server-side -- the client
verdict is never trusted. A dangerous (write/side-effecting) query is refused.
"""
from __future__ import absolute_import
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import splunk.admin as admin   
import splunk_io as sio         
import eai                    
from guardrail import Guardrail  


class RunHandler(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_CREATE:
            for arg in ("spl", "earliest", "latest", "validate_only"):
                self.supportedArgs.addOptArg(arg)

    def _first(self, key, default=""):
        return eai.first_arg(self.callerArgs, key, default)

    def handleList(self, confInfo):
        confInfo["result"].append("message", "POST spl, earliest?, latest? to execute a read-only search.")

    def handleCreate(self, confInfo):
        sk = self.getSessionKey()
        settings = sio.get_settings(sk)

        spl = self._first("spl", "").strip()
        if not spl:
            return self._out(confInfo, {"ok": False, "error": "spl is required"})

        
        verdict = Guardrail(settings.get("security", {})).check(spl)
        if not verdict["allowed"]:
            return self._out(confInfo, {
                "ok": False,
                "error": "Refused: the query contains write / side-effecting commands.",
                "risk_level": verdict["risk_level"],
                "issues": verdict["issues"],
            })

        validate_only = self._first("validate_only", "0").strip().lower() in ("1", "true", "yes", "on")
        if validate_only:
            return self._out(confInfo, {
                "ok": True,
                "validated": True,
                "risk_level": verdict["risk_level"],
                "issues": verdict["issues"],
            })

        q = settings.get("query", {}) or {}
        try:
            max_results = int(q.get("max_results", 1000))
        except (TypeError, ValueError):
            max_results = 1000
        try:
            timeout = int(q.get("timeout_seconds", 60))
        except (TypeError, ValueError):
            timeout = 60

        earliest = self._first("earliest", "-24h@h").strip() or "-24h@h"
        latest = self._first("latest", "now").strip() or "now"

        try:
            rows, truncated = sio.run_search(
                sk, spl, earliest=earliest, latest=latest,
                max_results=max_results, timeout=timeout,
            )
        except Exception as e:  
            return self._out(confInfo, {"ok": False, "error": "search failed: %s" % e})

        
        fields = list(rows[0].keys()) if rows else []
        self._out(confInfo, {
            "ok": True,
            "row_count": len(rows),
            "truncated": truncated,
            "risk_level": verdict["risk_level"],
            "issues": verdict["issues"],
            "fields": fields,
            "rows": rows,
        })

    @staticmethod
    def _out(confInfo, payload):
        confInfo["result"].append("json", json.dumps(payload))


if __name__ == "__main__":
    admin.init(RunHandler, admin.CONTEXT_APP_AND_USER)
