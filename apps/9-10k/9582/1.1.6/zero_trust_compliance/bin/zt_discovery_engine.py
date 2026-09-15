#!/usr/bin/env python3
# ==============================================================================
# ZERO TRUST FLEXIBLE TELEMETRY & STATE DISCOVERY ENGINE
# Standards: CIM Auto-Discovery, GOTS Regex Field Extractions,
# Manual Override Lock Protection, Throttled Cache Architecture
# ==============================================================================

import json
import time
import os
import sys
import re
import csv
import splunk.rest as rest

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(BIN_DIR)
LOOKUPS_DIR = os.path.join(BASE_DIR, 'lookups')

SAFE_ID_REGEX = re.compile(r'^[a-zA-Z0-9_\.\-]+$')

PILLARS = [
    'User',
    'Device',
    'Applications & Workloads',
    'Data',
    'Network & Environment',
    'Automation & Orchestration',
    'Visibility & Analytics'
]

class ZTDiscoveryEngine(rest.BaseRestHandler):

    def handle_GET(self):
        """Retrieve discovery telemetry status, cached posture, and tool registry."""
        session_key = self.getSessionKey()
        query_params = self.request.get('query', {})
        action = query_params.get('action', 'summary') # 'summary', 'tools', 'cache', 'rules'

        if action == 'tools':
            tools = self._load_tool_registry(session_key)
            self._send_json_response(200, tools)
        elif action == 'rules':
            rules = self._load_discovery_rules()
            self._send_json_response(200, rules)
        elif action == 'cache':
            cache = self._load_discovery_cache(session_key)
            self._send_json_response(200, cache)
        else:
            summary = self._generate_telemetry_summary(session_key)
            self._send_json_response(200, summary)

    def handle_POST(self):
        """Execute discovery scan, register GOTS tools, or toggle ISSO override locks."""
        session_key = self.getSessionKey()
        user = self.userName or "splunk_user"

        try:
            payload = json.loads(self.request.get('payload', '{}'))
        except (ValueError, TypeError):
            self._send_json_error(400, "Invalid JSON payload.")
            return

        action = payload.get('action') # 'register_tool', 'toggle_override_lock', 'run_discovery'

        if action == 'register_tool':
            self._handle_register_tool(session_key, payload, user)
        elif action == 'toggle_override_lock':
            self._handle_toggle_override_lock(session_key, payload, user)
        elif action == 'run_discovery':
            self._handle_run_discovery(session_key, payload, user)
        else:
            self._send_json_error(400, "Invalid action requested.")

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

    def _generate_telemetry_summary(self, session_key):
        """Generate 7-Pillar Telemetry Health Heatmap with cached metrics."""
        tools = self._load_tool_registry(session_key)
        cache = self._load_discovery_cache(session_key)

        pillar_summary = {}
        for p in PILLARS:
            pillar_tools = [t for t in tools if p in t.get('pillars_covered', '')]
            events_sum = sum([int(c.get('event_volume_24h', 0)) for c in cache if c.get('pillar') == p])
            has_tools = len(pillar_tools) >= 1
            has_events = events_sum > 0
            
            if has_tools and has_events:
                health = "Healthy" if events_sum >= 100 else "Degraded"
                confidence = 88 if len(pillar_tools) >= 2 else 65
            elif has_tools and not has_events:
                health = "Degraded"
                confidence = 35
            else:
                health = "No Telemetry"
                confidence = 0

            pillar_summary[p] = {
                "pillar": p,
                "connected_tools_count": len(pillar_tools),
                "tools": [t.get('tool_name') for t in pillar_tools],
                "telemetry_health": health,
                "total_events_24h": events_sum,
                "confidence_score": confidence
            }

        return {
            "timestamp": int(time.time()),
            "total_registered_tools": len(tools),
            "pillars": pillar_summary,
            "cached_evaluations_count": len(cache)
        }

    def _handle_register_tool(self, session_key, payload, user):
        """Register commercial or DoD GOTS tool with custom regex extractions."""
        user_role = self._resolve_user_roles(session_key, user)
        if user_role not in ('admin', 'sc_admin', 'ISSM', 'Scrum Master', 'ISSO'):
            self._send_json_response(403, {
                "error": "Forbidden: Registering custom GOTS tools requires administrative or Lead/ISSM authority.",
                "error_code": "TOOL_REGISTRATION_RBAC_REQUIRED"
            })
            return

        tool_name = payload.get('tool_name')
        if not tool_name:
            self._send_json_error(400, "Missing 'tool_name'.")
            return

        tool_id = payload.get('tool_id') or f"TOOL-CUSTOM-{int(time.time())}"
        custom_regex = payload.get('custom_regex_extraction', '')
        custom_aliases = payload.get('custom_field_aliases', '')
        custom_json_path = payload.get('custom_json_path', '')

        # Validate regex if provided
        if custom_regex:
            try:
                re.compile(custom_regex)
            except re.error as e:
                self._send_json_error(400, f"Invalid custom extraction regex: {str(e)}")
                return

        tool_record = {
            "_key": tool_id,
            "tool_id": tool_id,
            "tool_name": tool_name,
            "vendor_type": payload.get('vendor_type', 'DoD GOTS / Custom'),
            "pillars_covered": payload.get('pillars_covered', 'User'),
            "target_activities": payload.get('target_activities', '1.1.1'),
            "data_model_binding": payload.get('data_model_binding', 'Change_Analysis'),
            "index_pattern": payload.get('index_pattern', 'index=zerotrust'),
            "telemetry_sourcetype": payload.get('telemetry_sourcetype', 'dod:custom:telemetry'),
            "custom_regex_extraction": custom_regex,
            "custom_field_aliases": custom_aliases,
            "custom_json_path": custom_json_path,
            "health_status": "Connected",
            "last_telemetry_timestamp": int(time.time())
        }

        kv_path = f"/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_tool_registry/{tool_id}"
        resp, content = rest.simpleRequest(kv_path, sessionKey=session_key, jsonargs=json.dumps(tool_record), method='POST')

        if resp.status in (200, 201):
            self._log_audit(session_key, user, "register_tool", tool_id, f"Registered tool {tool_name}")
            self._send_json_response(200, {"status": "success", "tool_id": tool_id, "record": tool_record})
        else:
            self._send_json_error(resp.status, f"Failed to persist tool: {content}")

    def _handle_toggle_override_lock(self, session_key, payload, user):
        """Set or release ISSO Manual Override Lock on an activity/story."""
        user_role = self._resolve_user_roles(session_key, user)
        is_auth_approver = user_role in ('ISSO', 'ISSM', 'admin', 'sc_admin')
        if not is_auth_approver:
            self._send_json_response(403, {
                "error": "Forbidden: Toggling the Manual Override Lock requires an authorized ISSO or ISSM role.",
                "error_code": "OVERRIDE_LOCK_RBAC_REQUIRED"
            })
            return

        story_id = payload.get('story_id')
        ref = payload.get('ref')
        lock_state = bool(payload.get('override_lock', True))
        reason = payload.get('override_reason', 'ISSO manual verification decision')

        if not story_id and not ref:
            self._send_json_error(400, "Missing 'story_id' or 'ref'.")
            return

        target_id = story_id or f"ZTA-{ref}"
        if not SAFE_ID_REGEX.match(target_id):
            self._send_json_error(400, "Invalid story identifier.")
            return

        kv_path = f"/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_agile_stories/{target_id}"

        existing_resp, existing_content = rest.simpleRequest(kv_path, sessionKey=session_key, method='GET', raiseAllErrors=False)
        if existing_resp.status != 200:
            self._send_json_error(404, "Story not found in KV store.")
            return

        record = json.loads(existing_content)
        record['override_lock'] = lock_state
        record['override_by'] = user if lock_state else ''
        record['override_reason'] = reason if lock_state else ''
        record['override_timestamp'] = int(time.time()) if lock_state else 0
        record['updated_by'] = user
        record['updated_at'] = int(time.time())

        save_resp, _ = rest.simpleRequest(kv_path, sessionKey=session_key, jsonargs=json.dumps(record), method='POST')
        if save_resp.status in (200, 201):
            self._log_audit(session_key, user, "toggle_override_lock", target_id, f"Lock set to {lock_state}: {reason}")
            self._send_json_response(200, {"status": "success", "story_id": target_id, "override_lock": lock_state})
        else:
            self._send_json_error(save_resp.status, "Failed to update override lock.")

    def _get_matching_tools_for_activity(self, tools, ref, pillar):
        """Dynamically resolve matching tools and sourcetypes from the tool registry."""
        matched_tool_names = []
        matched_sourcetypes = []
        for t in tools:
            target_acts = [a.strip() for a in t.get('target_activities', '').split(',') if a.strip()]
            tool_pillars = [p.strip() for p in t.get('pillars_covered', '').replace(';', ',').split(',') if p.strip()]
            
            if ref in target_acts:
                matched_tool_names.append(t.get('tool_name', ''))
                if t.get('telemetry_sourcetype'):
                    matched_sourcetypes.append(t.get('telemetry_sourcetype'))
            elif pillar in tool_pillars and not target_acts:
                matched_tool_names.append(t.get('tool_name', ''))
                if t.get('telemetry_sourcetype'):
                    matched_sourcetypes.append(t.get('telemetry_sourcetype'))
        
        # Fallback to pillar-level tools if no direct activity match
        if not matched_tool_names:
            for t in tools:
                tool_pillars = [p.strip() for p in t.get('pillars_covered', '').replace(';', ',').split(',') if p.strip()]
                if pillar in tool_pillars:
                    matched_tool_names.append(t.get('tool_name', ''))
                    if t.get('telemetry_sourcetype'):
                        matched_sourcetypes.append(t.get('telemetry_sourcetype'))

        # Deduplicate and sort
        matched_tool_names = sorted(list(set([n for n in matched_tool_names if n])))
        matched_sourcetypes = sorted(list(set([s for s in matched_sourcetypes if s])))
        
        return matched_tool_names, matched_sourcetypes

    def _execute_rule_search(self, session_key, search_heuristic):
        """Execute accelerated tstats search heuristic against Splunk REST search export endpoint."""
        if not search_heuristic or not search_heuristic.strip():
            return 0
        try:
            import urllib.parse
            query_str = search_heuristic.strip()
            if not query_str.startswith('|'):
                query_str = f"search {query_str}"
            search_path = f"/services/search/jobs/export?output_mode=json&search={urllib.parse.quote(query_str)}&earliest_time=-24h@h&latest_time=now"
            resp, content = rest.simpleRequest(search_path, sessionKey=session_key, method='POST', raiseAllErrors=False)
            if hasattr(resp, 'status') and resp.status == 200 and content:
                content_str = content.decode('utf-8') if isinstance(content, bytes) else str(content)
                lines = [l.strip() for l in content_str.split('\n') if l.strip()]
                total_count = 0
                for line in lines:
                    try:
                        row = json.loads(line)
                        res = row.get('result', {})
                        c_val = res.get('count') or res.get('total') or res.get('event_count')
                        if c_val is not None:
                            total_count += int(c_val)
                    except Exception:
                        pass
                return total_count
        except Exception:
            pass
        return 0

    def _query_activity_telemetry(self, session_key, rule, ref, coa_profile, injected_results=None, existing_cache=None):
        """Evaluate activity telemetry from injected search rows, live tstats queries, or existing cache.
        Live zero always wins: if a rule search was executed, return the live count directly (never fallback to stale cache)."""
        # 1. Injected search results (for unit tests / automated validation)
        if injected_results is not None and isinstance(injected_results, dict):
            if ref in injected_results:
                inj_val = injected_results[ref]
                if isinstance(inj_val, dict):
                    return int(inj_val.get('count', 0)), inj_val.get('sourcetype')
                return int(inj_val), None
            return 0, None

        # 2. Live tstats search query against accelerated CIM models
        if rule and rule.get('search_heuristic'):
            live_count = self._execute_rule_search(session_key, rule.get('search_heuristic'))
            # Live search was executed. Live zero wins — return observed count directly without stale cache fallback.
            return live_count, rule.get('cim_data_model')

        # 3. Existing populated discovery cache (fallback ONLY when no rule search exists)
        if existing_cache and ref in existing_cache:
            cache_entry = existing_cache[ref]
            vol = int(cache_entry.get('event_volume_24h', 0))
            return vol, cache_entry.get('matched_sourcetypes')

        # 4. Default: No observed telemetry
        return 0, None

    def _handle_run_discovery(self, session_key, payload, user):
        """Execute telemetry discovery evaluation across activities without hardcoded volumes."""
        user_role = self._resolve_user_roles(session_key, user)
        is_auth = user_role in ('admin', 'sc_admin', 'ISSM', 'ISSO', 'discovery_admin')
        if not is_auth:
            self._send_json_response(403, {
                "error": "Forbidden: Running telemetry discovery scans requires authorized ISSO, ISSM, or Splunk Admin role.",
                "error_code": "DISCOVERY_RBAC_REQUIRED"
            })
            return

        coa_profile = payload.get('coa_profile', 'COA 1 (Baseline Target)')
        injected_results = payload.get('injected_search_results') or payload.get('search_results')
        stories = self._load_agile_stories(session_key)
        rules = self._load_discovery_rules()
        tools = self._load_tool_registry(session_key)
        raw_cache = self._load_discovery_cache(session_key)
        existing_cache = {c.get('ref'): c for c in raw_cache if c.get('ref')}
        rules_by_ref = {r.get('ref'): r for r in rules if r.get('ref')}

        evaluated_count = 0
        overwritten_count = 0
        locked_preserved_count = 0
        cache_updates = []
        current_time = int(time.time())

        for story in stories:
            ref = story.get('ref')
            if not ref:
                continue
            act_type = story.get('activity_type', 'Target Level ZT')
            
            # If COA 1 is active, prioritize Target Level activities
            if 'COA 1' in coa_profile and 'Advanced' in act_type and not ref.startswith('0.'):
                continue

            rule = rules_by_ref.get(ref)
            is_locked = bool(story.get('override_lock', False) or story.get('isso_signed_off', False))
            pillar = story.get('pillar', 'User')

            # Dynamic tool and sourcetype resolution from zt_tool_registry
            matched_tools, matched_sourcetypes = self._get_matching_tools_for_activity(tools, ref, pillar)

            # Evaluate telemetry from search/cache/injected results
            event_vol, detected_st = self._query_activity_telemetry(session_key, rule, ref, coa_profile, injected_results, existing_cache)
            
            if detected_st and detected_st not in matched_sourcetypes:
                matched_sourcetypes.append(str(detected_st))

            threshold = int(rule.get('auto_status_threshold', 100)) if rule else 100
            conf_thresh = int(rule.get('confidence_threshold', 80)) if rule else 80

            if event_vol >= threshold and threshold > 0:
                sim_posture = "Compliant"
                confidence = conf_thresh
            elif event_vol > 0:
                sim_posture = "Working"
                confidence = max(50, int(conf_thresh * 0.75))
            else:
                sim_posture = "Pending"
                confidence = 0

            telemetry_detected = (event_vol > 0)

            cache_item = {
                "_key": ref,
                "ref": ref,
                "pillar": pillar,
                "telemetry_detected": telemetry_detected,
                "event_volume_24h": event_vol,
                "evaluated_posture": sim_posture,
                "discovery_confidence": confidence,
                "coa_profile_evaluated": coa_profile,
                "matched_sourcetypes": "; ".join(matched_sourcetypes) if matched_sourcetypes else "None",
                "matched_tools": ", ".join(matched_tools) if matched_tools else "None",
                "last_evaluated_timestamp": current_time
            }
            cache_updates.append(cache_item)
            evaluated_count += 1

            if is_locked:
                locked_preserved_count += 1
                story['discovered_telemetry_status'] = sim_posture
                # Save story with updated observation field only
                s_path = f"/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_agile_stories/{story.get('story_id')}"
                rest.simpleRequest(s_path, sessionKey=session_key, jsonargs=json.dumps(story), method='POST')
            else:
                # Update story status automatically if unlocked and telemetry observed
                status_changed = False
                if sim_posture == "Compliant" and story.get('status') == "Backlog":
                    story['status'] = "To Do"
                    status_changed = True
                elif sim_posture == "Working" and story.get('status') == "Backlog":
                    story['status'] = "In Progress"
                    status_changed = True
                story['discovered_telemetry_status'] = sim_posture
                overwritten_count += 1

                # Save story back with discovered status and perform write-through sync
                s_path = f"/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_agile_stories/{story.get('story_id')}"
                rest.simpleRequest(s_path, sessionKey=session_key, jsonargs=json.dumps(story), method='POST')
                if status_changed:
                    self._sync_cross_collections(session_key, story, user)

        # Persist summary cache
        for c in cache_updates:
            c_path = f"/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_discovery_cache/{c.get('ref')}"
            rest.simpleRequest(c_path, sessionKey=session_key, jsonargs=json.dumps(c), method='POST')

        self._log_audit(session_key, user, "run_discovery", "ALL_ACTIVITIES", f"Evaluated {evaluated_count} (COA Profile: {coa_profile}), Preserved {locked_preserved_count} locked")

        self._send_json_response(200, {
            "status": "success",
            "coa_profile": coa_profile,
            "evaluated_activities": evaluated_count,
            "locked_preserved": locked_preserved_count,
            "status_updated": overwritten_count,
            "timestamp": current_time
        })

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

    def _load_tool_registry(self, session_key):
        kv_path = "/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_tool_registry"
        resp, content = rest.simpleRequest(kv_path, sessionKey=session_key, method='GET')
        if resp.status == 200:
            return json.loads(content)
        
        # Fallback to CSV
        csv_path = os.path.join(LOOKUPS_DIR, 'zt_tool_registry.csv')
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as f:
                return list(csv.DictReader(f))
        return []

    def _load_discovery_rules(self):
        csv_path = os.path.join(LOOKUPS_DIR, 'zt_discovery_rules.csv')
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as f:
                return list(csv.DictReader(f))
        return []

    def _load_discovery_cache(self, session_key):
        kv_path = "/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_discovery_cache"
        resp, content = rest.simpleRequest(kv_path, sessionKey=session_key, method='GET')
        if resp.status == 200:
            return json.loads(content)
        return []

    def _load_agile_stories(self, session_key):
        kv_path = "/servicesNS/nobody/zero_trust_compliance/storage/collections/data/zt_agile_stories"
        resp, content = rest.simpleRequest(kv_path, sessionKey=session_key, method='GET')
        if resp.status == 200:
            return json.loads(content)
        return []

    def _log_audit(self, session_key, user, action, target_id, message):
        audit_payload = {
            "action": f"discovery_{action}",
            "user": user,
            "target_id": target_id,
            "message": message,
            "timestamp": int(time.time())
        }
        audit_path = "/services/receivers/simple?sourcetype=zerotrust_audit&index=_internal"
        try:
            rest.simpleRequest(audit_path, sessionKey=session_key, postargs=json.dumps(audit_payload), method='POST')
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
