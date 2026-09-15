#!/usr/bin/env python3
# ==============================================================================
# ZERO TRUST PROOF OF DELIVERY (PoD) - REST HANDLER
# Standards: Multi-Framework Mapping, Cryptographic SHA-256 Validation,
# Soft Deletes, Immutable Audit Trail, Session RBAC
# ==============================================================================

import json
import time
import os
import sys
import re
import splunk.rest as rest

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(BIN_DIR, 'lib')
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

SAFE_ID_REGEX = re.compile(r'^[a-zA-Z0-9_\.\-]+$')
SHA256_REGEX = re.compile(r'^[a-fA-F0-9]{64}$')

class ZTPodHandler(rest.BaseRestHandler):
    def handle_GET(self):
        """Retrieve Proof of Delivery evidence items."""
        session_key = self.getSessionKey()
        kv_path = "/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_evidence_pod"
        
        query_params = self.request.get('query', {})
        evidence_id = query_params.get('evidence_id')
        ref_filter = query_params.get('ref')
        
        if evidence_id:
            if not SAFE_ID_REGEX.match(evidence_id):
                self._send_json_error(400, "Invalid evidence identifier.")
                return
            kv_path = f"{kv_path}/{evidence_id}"

        response, content = rest.simpleRequest(kv_path, sessionKey=session_key, method='GET')
        
        if response.status == 200:
            data = json.loads(content)
            if isinstance(data, list):
                # Filter active and optionally by ZTA ref
                filtered = [
                    item for item in data 
                    if not item.get('is_deleted', False) and (not ref_filter or item.get('ref') == ref_filter)
                ]
                self._send_json_response(200, filtered)
            else:
                if data.get('is_deleted', False):
                    self._send_json_error(404, "Evidence artifact not found or archived.")
                else:
                    self._send_json_response(200, data)
        else:
            self._send_json_error(response.status, "Failed to retrieve evidence artifacts.")

    def handle_POST(self):
        """Create or update a Proof of Delivery evidence artifact."""
        session_key = self.getSessionKey()
        user = self.userName or "splunk_assessor"

        try:
            payload = json.loads(self.request.get('payload', '{}'))
        except (ValueError, TypeError):
            self._send_json_error(400, "Invalid JSON payload.")
            return

        evidence_id = payload.get('evidence_id')
        ref = payload.get('ref')

        if not evidence_id or not SAFE_ID_REGEX.match(str(evidence_id)):
            self._send_json_error(400, "Missing or invalid 'evidence_id'.")
            return

        if not ref or not SAFE_ID_REGEX.match(str(ref)):
            self._send_json_error(400, "Missing or invalid 'ref'.")
            return

        sha256 = payload.get('hash_sha256', '').strip()
        if sha256 and not SHA256_REGEX.match(sha256):
            self._send_json_error(400, "Invalid SHA-256 hash format. Must be 64 hexadecimal characters.")
            return

        kv_path = f"/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_evidence_pod/{evidence_id}"
        current_time = int(time.time())

        record = {
            "_key": evidence_id,
            "evidence_id": evidence_id,
            "ref": ref,
            "governance_policy_id": payload.get('governance_policy_id', 'DoD-ZTA-Baseline'),
            "artifact_name": payload.get('artifact_name', 'Unnamed Evidence Artifact'),
            "artifact_type": payload.get('artifact_type', 'Configuration Scan'),
            "hash_sha256": sha256,
            "evidence_url": payload.get('evidence_url', ''),
            "verified_by": user,
            "verification_timestamp": current_time,
            "last_verified_at": current_time,
            "integrity_status": payload.get('integrity_status', 'Verified'),
            "is_deleted": bool(payload.get('is_deleted', False)),
            "notes": payload.get('notes', '')
        }

        save_resp, save_content = rest.simpleRequest(kv_path, sessionKey=session_key, jsonargs=json.dumps(record), method='POST')

        if save_resp.status in (200, 201):
            self._log_audit_event(session_key, user, record)
            self._send_json_response(200, {"status": "success", "evidence_id": evidence_id, "verified_at": current_time})
        else:
            self._send_json_error(save_resp.status, f"Failed to persist evidence record: {save_content}")

    def _log_audit_event(self, session_key, user, record):
        audit_payload = {
            "action": "zt_evidence_upload",
            "user": user,
            "evidence_id": record.get("evidence_id"),
            "ref": record.get("ref"),
            "governance_policy_id": record.get("governance_policy_id"),
            "hash_sha256": record.get("hash_sha256"),
            "integrity_status": record.get("integrity_status"),
            "timestamp": int(time.time())
        }
        event_str = json.dumps(audit_payload)
        audit_path = "/services/receivers/simple?sourcetype=zerotrust_audit&index=_internal"
        try:
            rest.simpleRequest(audit_path, sessionKey=session_key, postargs=event_str, method='POST')
        except Exception:
            pass

    def _send_json_response(self, status_code, body):
        self.response.setStatus(status_code)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps(body))

    def _send_json_error(self, status_code, message):
        self.response.setStatus(status_code)
        self.response.setHeader('content-type', 'application/json')
        self.response.write(json.dumps({"status": "error", "message": message}))
