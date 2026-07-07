#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

"""
Automatic label assignment — rule engine (pure, no I/O).

A tenant stores a JSON-encoded array of rules in the ``auto_labels_rules``
``vtenant_account`` field. Each rule auto-assigns one or more tenant labels
(from the ``kv_trackme_labels_tenant_<tid>`` catalog) to an entity when a
lifecycle trigger fires, optionally narrowed by the same priority + filter-DSL
gating used by the AI automated-action filter
(``is_ai_automated_eligible_for_entity`` in ``trackme_libs_mloutliers``).

This module is deliberately I/O-free so it can be exercised by unit tests and
called from the hot decision-maker loop without any KV access. The only
side-effecting consumer is the scheduled batch path
(``package/bin/trackmedecisionmaker.py``), which feeds it the entity record,
the prior/new state, and the per-entity ``auto_labels_applied`` marker, then
flushes the computed assignment deltas in a single batched write.

Design guarantees (product owner: "near no cost, scale, never fail anything"):
  * fail-open everywhere — a malformed rule, bad expression, or unexpected
    input degrades to "do nothing for this rule", never raises;
  * additive ``manual`` mode never removes a label and never resurrects one
    the user manually removed (guarded by the per-entity applied marker);
  * ``auto`` mode reconciles (adds while the condition holds, removes when it
    clears) but only ever touches labels an auto rule owns — labels that no
    enabled auto rule targets are left exactly as the user set them.
"""

import json

from trackme_filter_engine import apply_filter, validate_filter

# Valid enum values, single source of truth (shared by the save endpoint).
VALID_TRIGGERS = ("discovered", "enters_alert", "recovers", "custom_filter")
VALID_REMOVAL_MODES = ("manual", "auto")
# Priority-filter tokens. Matches the 4-level convention used everywhere else a
# priority filter is accepted (ML Outliers scope, ai_automated_priority_filter,
# the globalConfig regex). "pending" is intentionally excluded so it cannot pass
# validation here only to be silently dropped by the endpoint's canonical_order
# normalisation — an empty priority_filter already means "all priorities".
VALID_PRIORITIES = ("critical", "high", "medium", "low")

# Triggers whose condition is an instantaneous transition ("edge"). Edge
# triggers in ``manual`` mode fire on every transition and are NOT suppressed by
# the applied marker (re-entering alert is a new event, not a resurrection).
# Non-edge triggers (discovered, custom_filter) are state-based and DO use the
# marker so a ``manual`` rule fires at most once per entity.
_EDGE_TRIGGERS = ("enters_alert", "recovers")

_ALERT_STATES = ("red", "orange")


# ──────────────────────────────────────────────────────────────────────────────
# Priority CSV parsing (mirrors trackme_libs_mloutliers._parse_priority_filter_csv
# so the two filters behave identically).
# ──────────────────────────────────────────────────────────────────────────────
def _parse_priority_filter_csv(value):
    """Parse a comma-separated priority filter into a normalised lower-case set.
    Returns ``None`` when the filter is effectively empty (match-all)."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    items = {p.strip().lower() for p in raw.split(",") if p.strip()}
    return items or None


def _coerce_label_ids(value):
    """Best-effort coerce a rule's ``label_ids`` into a list of non-empty
    strings. Accepts a JSON-encoded string, a real list, or a single string.
    Never raises — returns ``[]`` on anything unusable."""
    if value is None:
        return []
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        # Could be a JSON array string or a single id / CSV.
        if raw[0] == "[":
            try:
                value = json.loads(raw)
            except Exception:
                return []
        else:
            return [p.strip() for p in raw.split(",") if p.strip()]
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in value:
            s = str(item).strip()
            if s:
                out.append(s)
        return out
    s = str(value).strip()
    return [s] if s else []


# ──────────────────────────────────────────────────────────────────────────────
# Rule parsing / validation
# ──────────────────────────────────────────────────────────────────────────────
def parse_auto_labels_rules(vtenant_account):
    """Read and normalise the ``auto_labels_rules`` JSON list from a tenant
    config dict. Fail-open: any problem yields ``[]`` (feature inert).

    Returns a list of normalised rule dicts. Each rule is guaranteed to carry:
    ``rule_id`` (str), ``enabled`` (bool), ``trigger`` (str, may be invalid —
    callers ignore unknown triggers), ``removal_mode`` (str), ``label_ids``
    (list[str]), ``priority_filter`` (str), ``filter_expression`` (str).
    Rules with no resolvable ``label_ids`` or an unknown trigger are dropped.
    """
    if not isinstance(vtenant_account, dict):
        return []
    raw = vtenant_account.get("auto_labels_rules", "[]")
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except Exception:
            return []
    else:
        parsed = raw
    if not isinstance(parsed, list):
        return []

    rules = []
    for idx, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        trigger = str(item.get("trigger", "")).strip()
        if trigger not in VALID_TRIGGERS:
            continue
        label_ids = _coerce_label_ids(item.get("label_ids"))
        if not label_ids:
            # A rule that targets no labels can never do anything — drop it
            # so the hot loop never iterates a no-op.
            continue
        removal_mode = str(item.get("removal_mode", "manual")).strip().lower()
        if removal_mode not in VALID_REMOVAL_MODES:
            removal_mode = "manual"
        # Discovery has no "exit" event — auto removal is meaningless, force manual.
        if trigger == "discovered":
            removal_mode = "manual"
        rule_id = str(item.get("rule_id", "") or "").strip() or f"rule_{idx}"
        enabled = item.get("enabled", True)
        enabled = bool(enabled) if not isinstance(enabled, str) else enabled.strip().lower() not in ("0", "false", "no", "")
        rules.append(
            {
                "rule_id": rule_id,
                "enabled": enabled,
                "trigger": trigger,
                "removal_mode": removal_mode,
                "label_ids": label_ids,
                "priority_filter": str(item.get("priority_filter", "") or "").strip(),
                "filter_expression": str(item.get("filter_expression", "") or "").strip(),
            }
        )
    return rules


def tenant_has_enabled_auto_labels(rules):
    """Cheap early-out gate: True iff at least one parsed rule is enabled.
    Tenants with no enabled rules do zero auto-label work in the batch path."""
    try:
        return any(r.get("enabled") for r in rules)
    except Exception:
        return False


def validate_auto_label_rule(rule):
    """Validate one raw rule dict for the save endpoint. Returns ``None`` when
    valid, otherwise a human-readable error string. Stricter than
    ``parse_auto_labels_rules`` (which silently drops bad rules) so the UI can
    surface precise feedback before persisting."""
    if not isinstance(rule, dict):
        return "rule must be an object"
    trigger = str(rule.get("trigger", "")).strip()
    if trigger not in VALID_TRIGGERS:
        return f"invalid trigger '{trigger}' (must be one of {', '.join(VALID_TRIGGERS)})"
    removal_mode = str(rule.get("removal_mode", "manual")).strip().lower()
    if removal_mode not in VALID_REMOVAL_MODES:
        return f"invalid removal_mode '{removal_mode}' (must be manual or auto)"
    # Discovery has no "exit" event, so removal_mode=auto is meaningless. Surface
    # it as an explicit error rather than silently coercing it to manual (the UI
    # hides the control for this trigger, so this only guards direct-API callers).
    if trigger == "discovered" and removal_mode == "auto":
        return "removal_mode 'auto' is not valid for the 'discovered' trigger (discovery has no exit event); use 'manual'"
    if not _coerce_label_ids(rule.get("label_ids")):
        return "rule must target at least one label (label_ids)"
    priority_filter = str(rule.get("priority_filter", "") or "").strip()
    if priority_filter:
        bad = [p for p in priority_filter.split(",") if p.strip() and p.strip().lower() not in VALID_PRIORITIES]
        if bad:
            return f"invalid priority value(s) in priority_filter: {', '.join(bad)}"
    expr = str(rule.get("filter_expression", "") or "").strip()
    if expr:
        err = validate_filter(expr)
        if err is not None:
            return f"invalid filter_expression: {err}"
    if trigger == "custom_filter" and not expr:
        return "custom_filter trigger requires a non-empty filter_expression"
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Per-rule eligibility (priority + filter DSL gate) — mirrors
# is_ai_automated_eligible_for_entity but reads the gate from the rule itself.
# ──────────────────────────────────────────────────────────────────────────────
def is_auto_label_eligible_for_entity(rule, entity_dict):
    """Decide whether ``entity_dict`` passes a rule's optional priority +
    filter-expression gate. Returns ``(eligible: bool, reason: str)``:
      - ""                          eligible
      - "priority_filter"           entity priority excluded by the CSV
      - "filter_expression"         entity does not match the expression
      - "filter_expression_invalid" the rule ships an unparseable expression
        (fail-closed — the rule does nothing rather than match everything)

    Fail-open on unexpected input (returns eligible) so a single bad rule can
    never block the rest of the loop.
    """
    if not isinstance(rule, dict) or not isinstance(entity_dict, dict):
        return True, ""

    priority_filter = _parse_priority_filter_csv(rule.get("priority_filter"))
    if priority_filter is not None:
        entity_priority = str(entity_dict.get("priority", "") or "").strip().lower()
        if entity_priority and entity_priority not in priority_filter:
            return False, "priority_filter"

    expr = str(rule.get("filter_expression", "") or "").strip()
    if expr:
        if validate_filter(expr) is not None:
            return False, "filter_expression_invalid"
        try:
            matched = apply_filter([entity_dict], expr)
        except Exception:
            matched = []
        if not matched:
            return False, "filter_expression"

    return True, ""


# ──────────────────────────────────────────────────────────────────────────────
# Core reconcile — the only stateful semantics, fully unit-tested.
# ──────────────────────────────────────────────────────────────────────────────
def _coerce_applied_map(applied_map):
    """Normalise the per-entity ``auto_labels_applied`` marker into
    ``{rule_id: [label_ids]}``. Accepts a JSON string or a dict; fail-open to
    ``{}``."""
    if applied_map is None:
        return {}
    if isinstance(applied_map, str):
        raw = applied_map.strip()
        if not raw:
            return {}
        try:
            applied_map = json.loads(raw)
        except Exception:
            return {}
    if not isinstance(applied_map, dict):
        return {}
    out = {}
    for k, v in applied_map.items():
        out[str(k)] = _coerce_label_ids(v)
    return out


def reconcile_entity_labels(
    rules, entity_dict, prior_state, new_state, is_new, applied_map, existing_label_ids
):
    """Compute the entity's final label_id set after applying every enabled
    rule for the current cycle.

    Args:
        rules: list of normalised rules (from ``parse_auto_labels_rules``).
        entity_dict: the entity record (needs ``priority`` / filter fields and,
            for ``component=...`` expressions, a ``component`` key).
        prior_state: the entity's previous ``object_state`` (``None`` for a
            brand-new entity).
        new_state: the freshly-computed ``object_state`` (green/orange/red/blue).
        is_new: True when the entity was just discovered this cycle. A new
            entity that is discovered already in an alert state fires
            ``enters_alert`` (in addition to ``discovered``), since from the
            tracker's perspective it has just entered alert.
        applied_map: the per-entity ``auto_labels_applied`` marker
            (``{rule_id: [label_ids]}``, JSON string or dict).
        existing_label_ids: the entity's current assignment ``label_ids``.

    Returns:
        ``(final_label_ids: list[str], updated_applied_map: dict, changed: bool)``
        ``changed`` is True iff the label set differs from ``existing_label_ids``.
        On any internal error the function fails open: returns the existing set
        unchanged so the batch path writes nothing for this entity.
    """
    try:
        existing = [str(x).strip() for x in (existing_label_ids or []) if str(x).strip()]
        existing_set = set(existing)
        applied = _coerce_applied_map(applied_map)
        # Snapshot the incoming marker so we can detect a marker-only change
        # (e.g. a manual custom_filter rule firing on an entity that already
        # carries the label): the label set is unchanged but the once-only
        # marker must still be persisted, or the rule could re-fire later.
        applied_before = {k: list(v) for k, v in applied.items()}

        additions = set()
        # All labels owned by an enabled auto rule (candidates for removal when
        # their condition no longer holds), and the subset currently asserted.
        auto_owned = set()
        auto_active = set()

        for rule in rules or []:
            if not isinstance(rule, dict) or not rule.get("enabled"):
                continue
            rule_id = rule.get("rule_id")
            trigger = rule.get("trigger")
            if trigger not in VALID_TRIGGERS:
                continue
            mode = rule.get("removal_mode", "manual")
            label_ids = rule.get("label_ids") or []
            if not label_ids:
                continue

            eligible, _reason = is_auto_label_eligible_for_entity(rule, entity_dict)

            # Standing condition (auto maintain) and edge condition (manual fire).
            if trigger == "discovered":
                edge = bool(is_new)
                standing = False  # discovery is forced manual; no standing state
            elif trigger == "enters_alert":
                # Fire on green -> alert, AND on a brand-new entity that is
                # discovered already in an alert state (it has no prior "green",
                # but it has just entered alert from the tracker's perspective).
                edge = (prior_state == "green" or is_new) and (new_state in _ALERT_STATES)
                standing = new_state in _ALERT_STATES
            elif trigger == "recovers":
                edge = (prior_state in _ALERT_STATES) and (new_state == "green")
                standing = new_state == "green"
            else:  # custom_filter
                edge = True  # the eligibility gate IS the condition
                standing = True

            if mode == "auto":
                auto_owned.update(label_ids)
                # "recovers" is special in auto mode: its standing state ("is
                # green") is the NORMAL condition for most entities, so a pure
                # standing-add would tag EVERY green entity — including ones that
                # have never been in alert. The label literally reads
                # "recovered", which is misleading on an always-green entity.
                # So latch the add on the recovery transition itself (edge:
                # red/orange -> green) and then HOLD it while the rule already
                # owns the label and the entity stays green. Consequences:
                #   - an always-green entity never hits the edge -> never tagged;
                #   - a real recovery tags it, and it persists while green;
                #   - a re-alert drops `standing` -> the label is retracted;
                #   - the next recovery re-fires the edge -> re-tagged.
                # Other triggers keep pure standing-add: for enters_alert /
                # custom_filter, simply BEING in the standing state (in alert /
                # matching the filter) IS the noteworthy condition to mark.
                if trigger == "recovers":
                    auto_present = (
                        standing and eligible and (edge or rule_id in applied_before)
                    )
                else:
                    auto_present = standing and eligible
                if auto_present:
                    additions.update(label_ids)
                    auto_active.update(label_ids)
                    applied[rule_id] = list(label_ids)
                else:
                    applied.pop(rule_id, None)
            else:  # manual
                if trigger in _EDGE_TRIGGERS:
                    # Fire on every transition; no permanent suppression.
                    if edge and eligible:
                        additions.update(label_ids)
                        applied[rule_id] = list(label_ids)
                else:
                    # Non-edge (discovered, custom_filter): fire at most once.
                    if rule_id not in applied and edge and eligible:
                        additions.update(label_ids)
                        applied[rule_id] = list(label_ids)

        # Removal: a label owned by an enabled auto rule whose condition no
        # longer holds is retracted — UNLESS another enabled rule asserts it
        # this cycle (additions) or a manual rule keeps it. Labels no auto rule
        # owns are never touched, so user-managed labels are preserved.
        removal = (auto_owned - auto_active) - additions

        final_set = (existing_set - removal) | additions
        # Preserve a stable order: keep existing order, append new ids sorted.
        final = [lid for lid in existing if lid in final_set]
        for lid in sorted(final_set - set(final)):
            final.append(lid)

        # changed when the label set OR the applied marker differs, so the
        # batch path (which persists only on changed=True) never drops a
        # marker-only update.
        changed = (set(final) != existing_set) or (applied != applied_before)
        return final, applied, changed
    except Exception:
        # Never let auto-labelling break the decision maker.
        return list(existing_label_ids or []), _coerce_applied_map(applied_map), False
