#!/usr/bin/env python3
# ==============================================================================
# ZERO TRUST COMPLIANCE - REST HANDLER
# Standards: Input Sanitization, Optimistic Concurrency Control, Soft Deletes,
# Immutable Audit Trail, Session RBAC
# ==============================================================================

import json
import time
import os
import sys
import re
import splunk.rest as rest

# Dynamically resolve bin/lib for bundled dependencies
BIN_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(BIN_DIR, 'lib')
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

SAFE_ID_REGEX = re.compile(r'^[a-zA-Z0-9_\.\-]+$')

class ZTComplianceHandler(rest.BaseRestHandler):
    def handle_GET(self):
        """Fetch Zero Trust compliance items from the KV Store."""
        session_key = self.getSessionKey()
        kv_path = "/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_compliance_items"
        
        # Parse query parameters if any
        query_params = self.request.get('query', {})
        target_ref = query_params.get('ref')
        
        if target_ref:
            if not SAFE_ID_REGEX.match(target_ref):
                self._send_json_error(400, "Invalid reference identifier format.")
                return
            kv_path = f"{kv_path}/{target_ref}"

        response, content = rest.simpleRequest(kv_path, sessionKey=session_key, method='GET')
        
        if response.status == 200:
            data = json.loads(content)
            # Filter out soft-deleted items if requesting collection list
            if isinstance(data, list):
                active_items = [item for item in data if not item.get('is_deleted', False)]
                self._send_json_response(200, active_items)
            else:
                if data.get('is_deleted', False):
                    self._send_json_error(404, "Item not found or has been archived.")
                else:
                    self._send_json_response(200, data)
        else:
            self._send_json_error(response.status, "Failed to retrieve compliance records.")

    def handle_POST(self):
        """Create or update a Zero Trust compliance item with optimistic concurrency control."""
        session_key = self.getSessionKey()
        user = self.userName or "splunk_user"

        try:
            payload = json.loads(self.request.get('payload', '{}'))
        except (ValueError, TypeError):
            self._send_json_error(400, "Invalid JSON payload.")
            return

        ref = payload.get('ref')
        if not ref or not SAFE_ID_REGEX.match(str(ref)):
            self._send_json_error(400, "Missing or invalid 'ref' parameter.")
            return

        kv_base = "/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_compliance_items"
        item_path = f"{kv_base}/{ref}"

        # Check existing record for optimistic locking
        existing_resp, existing_content = rest.simpleRequest(item_path, sessionKey=session_key, method='GET', raiseAllErrors=False)
        
        current_server_time = int(time.time())
        existing_record = None

        if existing_resp.status == 200:
            try:
                existing_record = json.loads(existing_content)
                client_updated_at = payload.get('client_updated_at')
                server_updated_at = existing_record.get('updated_at')

                # Concurrency check: If client timestamp is provided and older than server timestamp, reject
                if client_updated_at and server_updated_at and int(client_updated_at) < int(server_updated_at):
                    self._send_json_response(409, {
                        "error": "Conflict: Record was modified by another assessor.",
                        "error_code": "CONCURRENCY_CONFLICT",
                        "server_record": existing_record
                    })
                    return
            except Exception:
                pass

        # Prepare sanitized record
        action_type = "update" if existing_record else "create"
        is_soft_delete = payload.get('is_deleted', False)

        record = {
            "_key": ref,
            "ref": ref,
            "capability": payload.get('capability', existing_record.get('capability', '') if existing_record else ''),
            "requirement": payload.get('requirement', existing_record.get('requirement', '') if existing_record else ''),
            "pillar": payload.get('pillar', existing_record.get('pillar', '') if existing_record else ''),
            "phase": payload.get('phase', existing_record.get('phase', '') if existing_record else ''),
            "status": payload.get('status', existing_record.get('status', 'Pending') if existing_record else 'Pending'),
            "tool": payload.get('tool', existing_record.get('tool', '') if existing_record else ''),
            "activity_type": payload.get('activity_type', existing_record.get('activity_type', 'Target') if existing_record else 'Target'),
            "implementation_scope": payload.get('implementation_scope', existing_record.get('implementation_scope', 'Enterprise') if existing_record else 'Enterprise'),
            "assigned_team": payload.get('assigned_team', existing_record.get('assigned_team', '') if existing_record else ''),
            "wbs_code": payload.get('wbs_code', existing_record.get('wbs_code', '') if existing_record else ''),
            "milestone_id": payload.get('milestone_id', existing_record.get('milestone_id', '') if existing_record else ''),
            "disruption_score": int(payload.get('disruption_score', existing_record.get('disruption_score', 1) if existing_record else 1)),
            "completion_pct": float(payload.get('completion_pct', existing_record.get('completion_pct', 0.0) if existing_record else 0.0)),
            "remediation_notes": payload.get('remediation_notes', existing_record.get('remediation_notes', '') if existing_record else ''),
            "blockers": payload.get('blockers', existing_record.get('blockers', '') if existing_record else ''),
            "is_deleted": bool(is_soft_delete),
            "updated_by": user,
            "updated_at": current_server_time
        }

        # Save to KV Store
        save_resp, save_content = rest.simpleRequest(item_path, sessionKey=session_key, jsonargs=json.dumps(record), method='POST')

        if save_resp.status in (200, 201):
            # Log immutable audit event
            self._log_audit_event(session_key, user, action_type, record)
            self._send_json_response(200, {"status": "success", "ref": ref, "updated_at": current_server_time})
        else:
            self._send_json_error(save_resp.status, f"Failed to persist record: {save_content}")

    def _log_audit_event(self, session_key, user, action, record):
        """Write an immutable audit transaction to the configured audit index."""
        audit_payload = {
            "action": f"zt_item_{action}",
            "user": user,
            "ref": record.get("ref"),
            "pillar": record.get("pillar"),
            "status": record.get("status"),
            "completion_pct": record.get("completion_pct"),
            "is_deleted": record.get("is_deleted"),
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
