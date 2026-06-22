"""Pure tier resolution from a Cryptolens response.

This module is dependency-free (no Splunk imports) so it can be unit-
tested directly and re-used inside the proxy / setup handlers.

The 7 documented Cryptolens features (f1..f7):

  F1 valid_until      — license is time-limited; check `expires`.
  F2 node_lock_guid   — enforce strict GUID match against
                        `activatedMachines[].mid`. When false, fall
                        back to the tier's default node-lock policy.
  F3 professional     — tier dimension.
  F4 enterprise       — tier dimension.
  F5 msp              — tier dimension.
  F6 pov              — Proof of Value; shows the PoV badge.
  F7 nfr              — Not-for-Resale; gets MSP features, 1 year, no
                        node lock; shows the NFR badge.

Precedence when more than one tier flag is set (e.g. F4=true + F5=true,
or F5=true + F7=true): tier = max of (msp, enterprise, professional).
Badge: nfr > pov > free.

Effective tier downgrades to "personal" when the license has expired
(`expires` in the past). The Web UI is responsible for greying out
the previously-licensed tabs without destroying the user's
configuration.
"""

from datetime import datetime, timezone


TIER_PERSONAL = "personal"
TIER_PROFESSIONAL = "professional"
TIER_ENTERPRISE = "enterprise"
TIER_MSP = "msp"

BADGE_FREE = "free"
BADGE_POV = "pov"
BADGE_POV_MSP = "pov_msp"
BADGE_NFR = "nfr"
# v1.4.1 — paid-tier "edition" badges. Shown when no special-program flag
# (NFR / PoV) applies. Resolved off the EFFECTIVE tier so an expired or
# node-lock-mismatched paid license reads as free, not "Enterprise Edition".
# The MSP badge TEXT is install-configurable (itmip_ai_workbench.conf
# [branding] msp_badge_label) because MSPs white-label; Professional/Enterprise
# text is fixed in the frontend.
BADGE_PROFESSIONAL = "professional"
BADGE_ENTERPRISE = "enterprise"
BADGE_MSP = "msp"


def _edition_badge_for(effective_tier):
    """The tier-edition badge for an effective tier (no NFR/PoV flag set)."""
    return {
        TIER_ENTERPRISE: BADGE_ENTERPRISE,
        TIER_MSP: BADGE_MSP,
        TIER_PROFESSIONAL: BADGE_PROFESSIONAL,
    }.get(effective_tier, BADGE_FREE)

# Scale + license-mechanic caps per tier (numeric limits + node-lock +
# single-user). PER-FEATURE gating lives in CAPABILITY_MIN_TIER below — that
# is the single source of truth for features; caps_for() folds the legacy
# feature booleans back in, derived from it. F2=true on the license can
# elevate the node-lock enforcement to strict.
TIER_CAPS = {
    TIER_PERSONAL: {
        "max_orgs": 1,
        "max_bus_per_org": 1,
        "max_concurrent_sessions": 1,
        # v1.3.0 — Free/personal is genuinely single-USER: the first user
        # binds the install; everyone else is greyed until a license is
        # added. Enforced via the free-tier owner (see itmip_llm_bootstrap).
        "single_user": True,
        "node_locked": False,
    },
    TIER_PROFESSIONAL: {
        "max_orgs": 1,
        "max_bus_per_org": 3,
        "max_concurrent_sessions": None,  # unlimited
        "single_user": False,
        "node_locked": True,
    },
    TIER_ENTERPRISE: {
        "max_orgs": 1,
        "max_bus_per_org": None,
        "max_concurrent_sessions": None,
        "single_user": False,
        "node_locked": True,
    },
    TIER_MSP: {
        "max_orgs": None,
        "max_bus_per_org": None,
        "max_concurrent_sessions": None,
        "single_user": False,
        "node_locked": True,
    },
}


# ── Feature capability matrix (per-feature licensing) ─────────────────────
# Single source of truth for PER-FEATURE gating: a capability key -> the
# minimum effective tier that unlocks it. Future-extensible — adding a
# roadmap feature later is one line here + one tag on the feature.
# resolve_capabilities() is emitted by GET /services/itmip_llm/license so the
# frontend never hard-codes the matrix. Reserved roadmap keys (data_onboarding,
# platform_ops, reliability_llm_ops, *_dashboard, multi_model_orchestration)
# are defined now but their features don't exist yet — they're "prepared to
# hold the roadmap." Spec: instructions/FEATURE_LICENSING_SPEC.md
TIER_ORDER = [TIER_PERSONAL, TIER_PROFESSIONAL, TIER_ENTERPRISE, TIER_MSP]

CAPABILITY_MIN_TIER = {
    # Core generation — all tiers incl. personal (resolve True everywhere;
    # no enforcement needed, listed for completeness / discoverability).
    "spl_generation": TIER_PERSONAL,
    "dashboard_generation": TIER_PERSONAL,   # Simple XML + Studio
    "alert_generation": TIER_PERSONAL,
    "byok": TIER_PERSONAL,
    "multi_llm": TIER_PERSONAL,
    "knowledge_layer": TIER_PERSONAL,
    "skills_layer": TIER_PERSONAL,
    "template_authoring": TIER_PERSONAL,
    # Professional+ — OPERATIONS.
    "ml_generation": TIER_PROFESSIONAL,      # anomaly/forecast/cluster/predict
    "history": TIER_PROFESSIONAL,
    "tokens_costs": TIER_PROFESSIONAL,
    "in_splunk_awareness": TIER_PROFESSIONAL,  # TrackMe/ES/ITSI read-only context
    "data_onboarding": TIER_PROFESSIONAL,    # reserved — ships 1.5.0
    "platform_ops": TIER_PROFESSIONAL,       # reserved — ships 1.6.0
    "backups": TIER_PROFESSIONAL,
    # Enterprise+ — SECURITY + INTEGRATIONS + GOVERNANCE + RELIABILITY.
    "security_workflows": TIER_ENTERPRISE,   # ES/ITSI triage/investigation/RCA/hunt
    "mcp_servers": TIER_ENTERPRISE,
    "custom_http_tools": TIER_ENTERPRISE,
    "iam_gateway_hook": TIER_ENTERPRISE,
    "audit_logging": TIER_ENTERPRISE,        # (moved from professional)
    "governance_logging": TIER_ENTERPRISE,
    "reliability_llm_ops": TIER_ENTERPRISE,    # reserved — roadmap
    "ai_activity_dashboard": TIER_ENTERPRISE,  # reserved — roadmap
    "llm_health_dashboard": TIER_ENTERPRISE,   # reserved — roadmap
    "multi_model_orchestration": TIER_ENTERPRISE,  # reserved — roadmap
    # MSP.
    "multi_deployment": TIER_MSP,
}


def tier_at_least(effective_tier, min_tier):
    """True if effective_tier is >= min_tier in the upgrade order."""
    try:
        return TIER_ORDER.index(effective_tier) >= TIER_ORDER.index(min_tier)
    except ValueError:
        return False


def resolve_capabilities(effective_tier):
    """The full {capability: bool} map for an effective tier — THE per-feature
    licensing source of truth, emitted to the frontend and used server-side.
    Reserved roadmap keys resolve too (their feature just doesn't exist yet)."""
    return {
        cap: tier_at_least(effective_tier, min_tier)
        for cap, min_tier in CAPABILITY_MIN_TIER.items()
    }


def _truthy(v):
    return v is True or v == 1 or v == "true"


def _parse_expires(expires_iso):
    """Cryptolens emits ISO timestamps with microseconds; tolerate
    variable precision and the `Z` suffix."""
    if not expires_iso:
        return None
    s = expires_iso.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if "." in s and "+" not in s and "-" not in s.rsplit("T", 1)[-1]:
        s = s + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except Exception:
        try:
            return datetime.strptime(expires_iso[:19], "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        except Exception:
            return None


def resolve_tier(license_key_response, now=None, current_guid=None):
    """Turn a `licenseKey` dict (the inner Cryptolens object) into a
    structured state the rest of the app can reason about.

    `license_key_response` is the dict at `response["licenseKey"]`.
    `now` defaults to `datetime.now(utc)`; injectable for tests.
    `current_guid` is the live environment GUID; injectable for tests.

    Returns dict with: tier, effective_tier, badge, expires_at,
    expires_in_days, is_expired, node_locked, node_lock_ok, key,
    customer_name, notes, raw.
    """
    if not isinstance(license_key_response, dict):
        return _state(TIER_PERSONAL, None, BADGE_FREE)

    f1 = _truthy(license_key_response.get("f1"))
    f2 = _truthy(license_key_response.get("f2"))
    f3 = _truthy(license_key_response.get("f3"))
    f4 = _truthy(license_key_response.get("f4"))
    f5 = _truthy(license_key_response.get("f5"))
    f6 = _truthy(license_key_response.get("f6"))
    f7 = _truthy(license_key_response.get("f7"))

    # NFR is treated as MSP features (per spec). Tier max-wins.
    is_nfr = f7
    if f5 or is_nfr:
        tier = TIER_MSP
    elif f4:
        tier = TIER_ENTERPRISE
    elif f3:
        tier = TIER_PROFESSIONAL
    else:
        # No tier flag set at all — degrade to personal.
        tier = TIER_PERSONAL

    # Badge precedence: NFR > PoV > tier edition. The NFR/PoV badges are set
    # from the license flags here; the tier-edition fallback (Professional /
    # Enterprise / MSP / free) is filled once `effective_tier` is known, so an
    # expired or node-lock-mismatched license reads as free, not as its paid
    # edition (v1.4.1).
    badge = None
    if is_nfr:
        badge = BADGE_NFR
    elif f6:
        badge = BADGE_POV_MSP if tier == TIER_MSP else BADGE_POV

    expires_at = _parse_expires(license_key_response.get("expires"))
    now = now or datetime.now(timezone.utc)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    is_expired = bool(f1 and expires_at and expires_at < now)
    expires_in_days = None
    if expires_at:
        expires_in_days = max(0, (expires_at - now).days)

    # Node lock: NFR explicitly NOT node-locked. F2=true enforces
    # strictly; otherwise tier default.
    if is_nfr:
        node_locked_required = False
    elif f2:
        node_locked_required = True
    else:
        node_locked_required = TIER_CAPS[tier]["node_locked"]

    activated_machines = []
    activated_mids = []
    for m in (license_key_response.get("activatedMachines") or []):
        if not isinstance(m, dict):
            continue
        mid = m.get("mid")
        if not mid:
            continue
        activated_mids.append(mid)
        activated_machines.append({
            "mid": mid,
            "ip": m.get("ip"),
            "time": m.get("time"),
        })
    node_lock_ok = True
    if node_locked_required and current_guid:
        node_lock_ok = current_guid in activated_mids

    # Cryptolens uses maxNoOfMachines=0 to mean "unlimited". An NFR or MSP
    # license can be activated on multiple Splunk environments — that's
    # how an MSP runs one key across customer envs.
    raw_max = license_key_response.get("maxNoOfMachines")
    try:
        max_no_of_machines = int(raw_max) if raw_max is not None else None
    except (TypeError, ValueError):
        max_no_of_machines = None
    if max_no_of_machines == 0:
        max_no_of_machines = None  # 0 → unlimited per Cryptolens convention

    # Effective tier: if expired or node-lock mismatch, downgrade to
    # personal (admin can re-activate to restore).
    effective_tier = tier
    if is_expired or not node_lock_ok:
        effective_tier = TIER_PERSONAL

    # Fill the tier-edition badge now that effective_tier is known (only when
    # no NFR/PoV flag already claimed the badge above). Off effective_tier so a
    # lapsed paid license shows "free", not its edition.
    if badge is None:
        badge = _edition_badge_for(effective_tier)

    return {
        "tier": tier,
        "effective_tier": effective_tier,
        "badge": badge,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "expires_in_days": expires_in_days,
        "is_expired": is_expired,
        "is_time_limited": bool(f1),
        "node_locked_required": node_locked_required,
        "node_lock_ok": node_lock_ok,
        "activated_mids": activated_mids,
        "activated_machines": activated_machines,
        "max_no_of_machines": max_no_of_machines,
        "key": license_key_response.get("key"),
        "customer_name": (license_key_response.get("customer") or {}).get("name"),
        "customer_email": (license_key_response.get("customer") or {}).get("email"),
        "notes": license_key_response.get("notes"),
        "feature_flags": {
            "f1": f1, "f2": f2, "f3": f3, "f4": f4,
            "f5": f5, "f6": f6, "f7": f7,
        },
    }


def _state(tier, expires_at, badge):
    return {
        "tier": tier,
        "effective_tier": tier,
        "badge": badge,
        "expires_at": expires_at,
        "expires_in_days": None,
        "is_expired": False,
        "is_time_limited": False,
        "node_locked_required": TIER_CAPS[tier]["node_locked"],
        "node_lock_ok": True,
        "activated_mids": [],
        "activated_machines": [],
        "max_no_of_machines": None,
        "key": None,
        "customer_name": None,
        "customer_email": None,
        "notes": None,
        "feature_flags": {},
    }


def caps_for(effective_tier):
    """Scale/mechanic caps for a tier PLUS the legacy feature booleans
    (history_enabled / tokens_tab_enabled / audit_enabled) DERIVED from the
    capability matrix. Back-compat for existing consumers; CAPABILITY_MIN_TIER
    is authoritative — e.g. audit_enabled now follows audit_logging (enterprise)."""
    base = dict(TIER_CAPS.get(effective_tier, TIER_CAPS[TIER_PERSONAL]))
    caps = resolve_capabilities(effective_tier)
    base["history_enabled"] = caps["history"]
    base["tokens_tab_enabled"] = caps["tokens_costs"]
    base["audit_enabled"] = caps["audit_logging"]
    return base
