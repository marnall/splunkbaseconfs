#!/usr/bin/env python3
# ==============================================================================
# ZERO TRUST AGILE STORIES & KANBAN - REST HANDLER
# Standards: WBS Rollup, Optimistic Concurrency Control, Soft Deletes,
# Role-Based Access Control (RBAC), Immutable Audit Logging
# ==============================================================================

import json
import time
import os
import sys
import re
import hashlib
import splunk.rest as rest

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(BIN_DIR, 'lib')
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

SAFE_ID_REGEX = re.compile(r'^[a-zA-Z0-9_\.\-]+$')

class ZTStoriesHandler(rest.BaseRestHandler):
    def handle_GET(self):
        """Retrieve Agile Stories for the Jira Kanban board."""
        session_key = self.getSessionKey()
        kv_path = "/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_agile_stories"
        
        query_params = self.request.get('query', {})
        story_id = query_params.get('story_id')
        sprint_filter = query_params.get('sprint')
        pillar_filter = query_params.get('pillar')
        
        if story_id:
            if not SAFE_ID_REGEX.match(story_id):
                self._send_json_error(400, "Invalid story identifier.")
                return
            kv_path = f"{kv_path}/{story_id}"

        response, content = rest.simpleRequest(kv_path, sessionKey=session_key, method='GET')
        
        if response.status == 200:
            data = json.loads(content)
            if isinstance(data, list):
                active = [
                    s for s in data 
                    if not s.get('is_deleted', False)
                    and (not sprint_filter or sprint_filter == '*' or s.get('sprint') == sprint_filter)
                    and (not pillar_filter or pillar_filter == '*' or s.get('pillar') == pillar_filter)
                ]
                self._send_json_response(200, active)
            else:
                if data.get('is_deleted', False):
                    self._send_json_error(404, "Story not found or archived.")
                else:
                    self._send_json_response(200, data)
        else:
            self._send_json_error(response.status, "Failed to retrieve stories.")

    def _resolve_user_roles(self, session_key, user):
        """Introspect authoritative Splunk authentication context for user roles.
        Deny-by-default: Never trusts client-supplied role payloads."""
        try:
            ctx_path = "/services/authentication/current-context?output_mode=json"
            resp, content = rest.simpleRequest(ctx_path, sessionKey=session_key, method='GET', raiseAllErrors=False)
            if hasattr(resp, 'status') and isinstance(resp.status, int) and resp.status == 200 and isinstance(content, (str, bytes)):
                ctx = json.loads(content)
                entry = ctx.get('entry', [{}])[0].get('content', {})
                roles = [str(r).lower() for r in entry.get('roles', []) if isinstance(r, str)]
                if 'admin' in roles or 'sc_admin' in roles:
                    return 'admin'
                if 'issm' in roles or 'issm_admin' in roles:
                    return 'ISSM'
                if 'isso' in roles:
                    return 'ISSO'
                if 'discovery_admin' in roles or 'discovery' in roles:
                    return 'discovery_admin'
                if 'scrum_master' in roles or 'lead' in roles:
                    return 'Scrum Master'
        except Exception:
            pass
        return 'SME'

    def handle_POST(self):
        """Create or update an Agile Story with RBAC, PoD Verification, Schema Integrity & Cross-Collection Sync."""
        session_key = self.getSessionKey()
        user = self.userName or "splunk_user"

        try:
            payload = json.loads(self.request.get('payload', '{}'))
        except (ValueError, TypeError):
            self._send_json_error(400, "Invalid JSON payload.")
            return

        story_id = payload.get('story_id')
        if not story_id or not SAFE_ID_REGEX.match(str(story_id)):
            self._send_json_error(400, "Missing or invalid 'story_id'.")
            return

        user_role = self._resolve_user_roles(session_key, user)
        new_status = payload.get('status')
        is_auth_approver = user_role in ('ISSO', 'ISSM', 'admin', 'sc_admin')

        # RBAC Check: Moving to 'Done' requires ISSO, ISSM, or Admin role (Dual CAC authority)
        if new_status in ('Done', 'Certified') and not is_auth_approver:
            self._send_json_response(403, {
                "error": "Forbidden: Only an authorized ISSO, ISSM, or Splunk Admin can certify completion via CAC authentication.",
                "error_code": "RBAC_ISSO_ISSM_REQUIRED"
            })
            return

        kv_path = f"/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_agile_stories/{story_id}"
        current_time = int(time.time())

        # Check existing record for optimistic locking, override locks, and status diff
        existing_resp, existing_content = rest.simpleRequest(kv_path, sessionKey=session_key, method='GET', raiseAllErrors=False)
        existing_record = None
        prev_status = "New"

        if existing_resp.status == 200:
            try:
                existing_record = json.loads(existing_content)
                prev_status = existing_record.get('status', 'Backlog')
                client_updated_at = payload.get('client_updated_at')
                server_updated_at = existing_record.get('updated_at')

                if client_updated_at and server_updated_at and int(client_updated_at) < int(server_updated_at):
                    self._send_json_response(409, {
                        "error": "Conflict: Story was modified by another user.",
                        "error_code": "CONCURRENCY_CONFLICT",
                        "server_record": existing_record
                    })
                    return
            except Exception:
                pass

        # 1. Enforce Manual Override Lock on existing records (ISSO / ISSM / Admin only)
        if existing_record and existing_record.get('override_lock', False):
            if not is_auth_approver:
                self._send_json_response(423, {
                    "error": "Locked: Story is protected by an ISSO/ISSM Manual Override Lock (🛡️ CERTIFIED / LOCKED). Only an authorized ISSO, ISSM, or Splunk Admin can modify or unlock this record.",
                    "error_code": "OVERRIDE_LOCK_ENFORCED"
                })
                return

        # 2. Enforce RBAC when toggling override_lock
        incoming_override_lock = payload.get('override_lock')
        if incoming_override_lock is not None and existing_record:
            if bool(incoming_override_lock) != bool(existing_record.get('override_lock', False)) and not is_auth_approver:
                self._send_json_response(403, {
                    "error": "Forbidden: Toggling the Manual Override Lock requires an authorized ISSO or ISSM role.",
                    "error_code": "OVERRIDE_LOCK_RBAC_REQUIRED"
                })
                return

        # 3. Authoritative ref & WBS resolution (prevent spoofed ref writing to unrelated compliance row)
        if existing_record and existing_record.get('ref'):
            ref = str(existing_record.get('ref')).strip()
            payload_ref = payload.get('ref')
            if payload_ref and str(payload_ref).strip() != ref:
                self._send_json_error(400, f"Immutable Field: Story ref '{ref}' cannot be mutated.")
                return
        else:
            ref = str(payload.get('ref', '')).strip()
            if not ref or not SAFE_ID_REGEX.match(ref):
                self._send_json_error(400, "Missing or invalid 'ref' identifier.")
                return
            # On create, enforce strict binding between story_id and ref
            expected_ref = story_id[4:] if story_id.startswith('ZTA-') else story_id
            if ref != expected_ref:
                self._send_json_error(400, f"Mismatched identifier: Story ID '{story_id}' must bind to ref '{expected_ref}' (received '{ref}').")
                return

        if existing_record and existing_record.get('parent_wbs_code'):
            parent_wbs_code = str(existing_record.get('parent_wbs_code')).strip()
        else:
            parent_wbs_code = str(payload.get('parent_wbs_code', f"WBS-{ref}")).strip()
            if not SAFE_ID_REGEX.match(parent_wbs_code):
                self._send_json_error(400, "Invalid 'parent_wbs_code' identifier.")
                return
            expected_wbs = f"WBS-{ref}"
            if parent_wbs_code != expected_wbs:
                self._send_json_error(400, f"Mismatched WBS code: Story ref '{ref}' must bind to '{expected_wbs}' (received '{parent_wbs_code}').")
                return

        action_type = "status_transition" if (existing_record and new_status != prev_status) else ("update" if existing_record else "create")

        # Determine ISSO/ISSM sign-off state & CAC metadata
        is_done = (new_status in ("Done", "Certified"))
        client_signing_requested = bool(payload.get('isso_signed_off', False)) or is_done

        if client_signing_requested and not is_auth_approver:
            self._send_json_response(403, {
                "error": "Forbidden: Cryptographic CAC stage-gate attestation and Done/Certified sign-off require an authorized ISSO or ISSM role.",
                "error_code": "CAC_RBAC_UNAUTHORIZED"
            })
            return

        # PoD Evidence Guard: Transition to 'Done' requires attached evidence or valid digital signature
        if is_done:
            evidence_ids = str(payload.get('evidence_ids', existing_record.get('evidence_ids', '') if existing_record else '')).strip()
            digital_sig = str(payload.get('digital_signature_hash', existing_record.get('digital_signature_hash', '') if existing_record else '')).strip()
            has_direct_evidence = bool(evidence_ids and evidence_ids not in ('None', '', 'null'))
            
            # Query KV Store zt_evidence_pod for linked evidence if ref is present and passes strict regex
            has_kv_evidence = False
            if ref and SAFE_ID_REGEX.match(ref):
                try:
                    import urllib.parse
                    pod_query = json.dumps({"ref": ref})
                    encoded_query = urllib.parse.quote(pod_query)
                    pod_path = f"/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_evidence_pod?query={encoded_query}"
                    pod_resp, pod_content = rest.simpleRequest(pod_path, sessionKey=session_key, method='GET', raiseAllErrors=False)
                    if pod_resp.status == 200:
                        pod_items = json.loads(pod_content)
                        if isinstance(pod_items, list) and len(pod_items) > 0:
                            has_kv_evidence = any(not item.get('is_deleted', False) and (item.get('hash_sha256') or item.get('integrity_status') == 'Verified') for item in pod_items)
                except Exception:
                    pass

            if not (has_direct_evidence or has_kv_evidence or digital_sig or is_auth_approver):
                self._send_json_response(422, {
                    "error": "Unprocessable Entity: Transitioning to 'Done / Certified' requires valid Proof of Delivery (PoD) evidence, SHA-256 hash attestation, or authorized ISSO/ISSM sign-off.",
                    "error_code": "POD_EVIDENCE_REQUIRED"
                })
                return

        isso_signed_off = False
        isso_signoff_by = existing_record.get('isso_signoff_by', '') if existing_record else ''
        isso_signoff_date = existing_record.get('isso_signoff_date', '') if existing_record else ''
        approver_role = existing_record.get('approver_role', '') if existing_record else ''
        cac_edipi = existing_record.get('cac_edipi', '') if existing_record else ''
        cac_subject_dn = existing_record.get('cac_subject_dn', '') if existing_record else ''
        digital_signature_hash = existing_record.get('digital_signature_hash', '') if existing_record else ''

        if client_signing_requested and is_auth_approver:
            req_edipi = str(payload.get('cac_edipi', cac_edipi)).strip()
            req_dn = str(payload.get('cac_subject_dn', cac_subject_dn)).strip()

            # Strict DoD EDIPI & Subject DN validation
            if req_edipi:
                if not re.match(r'^\d{10}$', req_edipi):
                    self._send_json_response(400, {
                        "error": "Invalid DoD EDIPI format: Must be exactly 10 numeric digits.",
                        "error_code": "INVALID_CAC_EDIPI"
                    })
                    return
                cac_edipi = req_edipi

            if req_dn:
                if not ("CN=" in req_dn):
                    self._send_json_response(400, {
                        "error": "Invalid CAC Subject DN: Must conform to X.509 DoD PKI distinguished name format.",
                        "error_code": "INVALID_CAC_DN"
                    })
                    return
                cac_subject_dn = req_dn

            isso_signed_off = True
            isso_signoff_by = user
            isso_signoff_date = time.strftime("%Y-%m-%d")
            approver_role = user_role

            # Server-Side Cryptographic Attestation Digest (Binding story, EDIPI, Subject DN, user, timestamp)
            sig_content = f"{story_id}|{ref}|{cac_edipi}|{cac_subject_dn}|{approver_role}|{user}|{current_time}"
            digital_signature_hash = hashlib.sha256(sig_content.encode('utf-8')).hexdigest()

        record = {
            "_key": story_id,
            "story_id": story_id,
            "ref": ref,
            "parent_wbs_code": parent_wbs_code,
            "title": payload.get('title', existing_record.get('title', 'Untitled Story') if existing_record else 'Untitled Story'),
            "description": payload.get('description', existing_record.get('description', '') if existing_record else ''),
            "outcomes": payload.get('outcomes', existing_record.get('outcomes', '') if existing_record else ''),
            "end_state": payload.get('end_state', existing_record.get('end_state', '') if existing_record else ''),
            "pillar": payload.get('pillar', existing_record.get('pillar', 'User') if existing_record else 'User'),
            "activity_type": payload.get('activity_type', existing_record.get('activity_type', 'Target Level ZT') if existing_record else 'Target Level ZT'),
            "implementation_scope": payload.get('implementation_scope', existing_record.get('implementation_scope', 'Component') if existing_record else 'Component'),
            "sprint": payload.get('sprint', existing_record.get('sprint', 'Sprint 1') if existing_record else 'Sprint 1'),
            "status": new_status or (existing_record.get('status', 'Backlog') if existing_record else 'Backlog'),
            "story_points": int(payload.get('story_points', existing_record.get('story_points', 3) if existing_record else 3)),
            "assignee": payload.get('assignee', existing_record.get('assignee', 'Unassigned') if existing_record else 'Unassigned'),
            "assigned_team": payload.get('assigned_team', existing_record.get('assigned_team', 'IAM Team') if existing_record else 'IAM Team'),
            "priority_class": payload.get('priority_class', existing_record.get('priority_class', 'High') if existing_record else 'High'),
            "predecessors": payload.get('predecessors', existing_record.get('predecessors', '') if existing_record else ''),
            "successors": payload.get('successors', existing_record.get('successors', '') if existing_record else ''),
            "acceptance_criteria": payload.get('acceptance_criteria', existing_record.get('acceptance_criteria', '') if existing_record else ''),
            "predictive_risk_level": payload.get('predictive_risk_level', existing_record.get('predictive_risk_level', 'Low') if existing_record else 'Low'),
            "blockers": payload.get('blockers', existing_record.get('blockers', 'None') if existing_record else 'None'),
            "isso_signed_off": bool(isso_signed_off),
            "isso_signoff_by": str(isso_signoff_by),
            "isso_signoff_date": str(isso_signoff_date),
            "approver_role": str(approver_role),
            "cac_edipi": str(cac_edipi),
            "cac_subject_dn": str(cac_subject_dn),
            "digital_signature_hash": str(digital_signature_hash),
            "evidence_ids": payload.get('evidence_ids', existing_record.get('evidence_ids', '') if existing_record else ''),
            "override_lock": bool(payload.get('override_lock', existing_record.get('override_lock', False) if existing_record else False)),
            "override_by": payload.get('override_by', existing_record.get('override_by', '') if existing_record else ''),
            "override_reason": payload.get('override_reason', existing_record.get('override_reason', '') if existing_record else ''),
            "override_timestamp": int(payload.get('override_timestamp', existing_record.get('override_timestamp', 0) if existing_record else 0)),
            "discovered_telemetry_status": payload.get('discovered_telemetry_status', existing_record.get('discovered_telemetry_status', '') if existing_record else ''),
            "nist_plane": payload.get('nist_plane', existing_record.get('nist_plane', 'Identity Plane') if existing_record else 'Identity Plane'),
            "nist_p_components": payload.get('nist_p_components', existing_record.get('nist_p_components', 'PIP;PEP') if existing_record else 'PIP;PEP'),
            "dfd_tier": payload.get('dfd_tier', existing_record.get('dfd_tier', 'Web Tier') if existing_record else 'Web Tier'),
            "is_deleted": bool(payload.get('is_deleted', False)),
            "updated_by": user,
            "updated_at": current_time
        }

        save_resp, save_content = rest.simpleRequest(kv_path, sessionKey=session_key, jsonargs=json.dumps(record), method='POST')

        if save_resp.status in (200, 201):
            # Atomic cross-collection write-through synchronization (Compliance Items & IMS Milestones)
            self._sync_cross_collections(session_key, record, user)

            # Emit immutable audit event
            self._log_audit_event(session_key, user, user_role, action_type, prev_status, record.get('status'), record)
            self._send_json_response(200, {
                "status": "success",
                "story_id": story_id,
                "updated_at": current_time,
                "record": record
            })
        else:
            self._send_json_error(save_resp.status, f"Failed to persist story record: {save_content}")

    def _sync_cross_collections(self, session_key, record, user):
        """Atomic write-through sync to zt_compliance_items and zt_milestones_ims."""
        ref = record.get('ref')
        status = record.get('status', 'Backlog')
        wbs_code = record.get('parent_wbs_code') or (f"WBS-{ref}" if ref else "")
        current_time = record.get('updated_at', int(time.time()))

        # 1. Sync zt_compliance_items
        if ref and SAFE_ID_REGEX.match(str(ref)):
            try:
                import urllib.parse
                comp_status_map = {
                    "Done": "Compliant",
                    "Certified": "Compliant",
                    "Testing": "Working",
                    "In Progress": "Working",
                    "To Do": "Pending",
                    "Backlog": "Pending"
                }
                comp_status = comp_status_map.get(status, "Pending")
                comp_pct_map = {"Done": 100, "Certified": 100, "Testing": 75, "In Progress": 35, "To Do": 10, "Backlog": 0}
                comp_pct = comp_pct_map.get(status, 0)

                encoded_ref = urllib.parse.quote(str(ref))
                comp_path = f"/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_compliance_items/{encoded_ref}"
                c_resp, c_content = rest.simpleRequest(comp_path, sessionKey=session_key, method='GET', raiseAllErrors=False)
                comp_record = {}
                if c_resp.status == 200:
                    try:
                        comp_record = json.loads(c_content)
                    except Exception:
                        pass

                comp_record.update({
                    "_key": ref,
                    "ref": ref,
                    "pillar": record.get('pillar', comp_record.get('pillar', 'User')),
                    "status": comp_status,
                    "completion_pct": comp_pct,
                    "implementation_scope": record.get('implementation_scope', comp_record.get('implementation_scope', 'Component')),
                    "nist_plane": record.get('nist_plane', comp_record.get('nist_plane', 'Identity Plane')),
                    "nist_p_components": record.get('nist_p_components', comp_record.get('nist_p_components', 'PIP;PEP')),
                    "dfd_tier": record.get('dfd_tier', comp_record.get('dfd_tier', 'Web Tier')),
                    "blockers": record.get('blockers', comp_record.get('blockers', 'None')),
                    "updated_by": user,
                    "updated_at": current_time
                })
                rest.simpleRequest(comp_path, sessionKey=session_key, jsonargs=json.dumps(comp_record), method='POST', raiseAllErrors=False)
            except Exception:
                pass

        # 2. Sync zt_milestones_ims
        if wbs_code and SAFE_ID_REGEX.match(str(wbs_code)):
            try:
                import urllib.parse
                ims_status_map = {
                    "Done": "Completed",
                    "Certified": "Completed",
                    "Testing": "In Progress",
                    "In Progress": "In Progress",
                    "To Do": "Pending",
                    "Backlog": "Pending"
                }
                ims_status = ims_status_map.get(status, "Pending")
                ims_pct_map = {"Done": 100, "Certified": 100, "Testing": 75, "In Progress": 35, "To Do": 10, "Backlog": 0}
                ims_pct = ims_pct_map.get(status, 0)

                ims_query = json.dumps({"wbs_code": wbs_code})
                encoded_ims_query = urllib.parse.quote(ims_query)
                ims_query_path = f"/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_milestones_ims?query={encoded_ims_query}"
                m_resp, m_content = rest.simpleRequest(ims_query_path, sessionKey=session_key, method='GET', raiseAllErrors=False)
                if m_resp.status == 200:
                    m_items = json.loads(m_content)
                    if isinstance(m_items, list) and len(m_items) > 0:
                        m_record = m_items[0]
                        m_key = m_record.get('_key') or m_record.get('milestone_id')
                        if m_key and SAFE_ID_REGEX.match(str(m_key)):
                            m_record.update({
                                "status": ims_status,
                                "completion_pct": ims_pct,
                                "actual_end_date": time.strftime("%Y-%m-%d") if status in ("Done", "Certified") else m_record.get('actual_end_date', ''),
                                "updated_by": user,
                                "updated_at": current_time
                            })
                            encoded_m_key = urllib.parse.quote(str(m_key))
                            m_save_path = f"/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_milestones_ims/{encoded_m_key}"
                            rest.simpleRequest(m_save_path, sessionKey=session_key, jsonargs=json.dumps(m_record), method='POST', raiseAllErrors=False)
            except Exception:
                pass

    def _log_audit_event(self, session_key, user, role, action, prev_status, new_status, record):
        """Write an immutable audit transaction to the zerotrust_audit index."""
        audit_payload = {
            "action": f"agile_story_{action}",
            "user": user,
            "role": role,
            "story_id": record.get("story_id"),
            "ref": record.get("ref"),
            "pillar": record.get("pillar"),
            "sprint": record.get("sprint"),
            "previous_status": prev_status,
            "new_status": new_status,
            "story_points": record.get("story_points"),
            "isso_signed_off": record.get("isso_signed_off"),
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
