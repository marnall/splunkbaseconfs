# Inno Observability for Splunk
# Copyright (c) 2026 Inno Software. All rights reserved.
#
# PROPRIETARY AND CONFIDENTIAL. Licensed, not sold — use requires a valid
# license key from Inno Software. Copying, redistribution, or removal of
# this notice is prohibited. See LICENSE.txt in this package.
# support@innosw.net · https://innosw.net/observability/terms.html
"""
Offline license-key verification for the Inno Splunk apps.

Ported from the Inno Streaming Add-on for AWS S3 (`ta_license.py`). The vendor
signs a license payload with a PRIVATE key; the app ships only the PUBLIC key
(`license_pubkey.pem`) and verifies offline -- NO network, NO activation server.
Customers are typically air-gapped, so a phone-home design is not an option.

Verification uses pure-Python RSA (the bundled `rsa` package), so there is no
compiled binary and the app still passes Splunk Cloud AppInspect.

License key string format:  <b64url(payload_json)>.<b64url(signature)>
  payload_json = {"product"|"products", "customer", "edition", "expiry":"YYYY-MM-DD",
                  "features":[], "issued", "splunk_manager_guid":[], "splunk_guid":[],
                  "grace_days", "provisional"}
  signature    = RSA SHA-256 over the exact payload_json bytes

DIFFERENCES FROM THE S3 ADD-ON (see docs/ip-protection-and-licensing-plan.md 5.1):
  * Node-lock anchor is the Splunk LICENSE MANAGER GUID (`manager_guid`), not an
    AWS account. One value covers a whole deployment -- every SHC member, indexer
    and license slave reports the same `manager_guid` -- so a distributed customer
    needs one entry, while a different customer site is a different manager.
  * The installed Splunk LICENSE is deliberately NOT an anchor. Measured on
    2026-07-26: Forwarder/Free license GUIDs are worldwide constants
    (1111.... / 0000....) and the partner NFR file is identical across partners,
    so a license-based unlock would collide exactly where the threat lives.
    License identity is recorded as AUDIT EVIDENCE only.
  * `product` is derived from the containing app directory, so this one file is
    shipped verbatim to both inno_observability and inno_dashboard_studio.

SECURITY NOTE (documented for honesty, per project convention): because app source
is readable (required by Splunk Cloud), a signed key stops forging and sharing of
keys and gives the EULA legal teeth, but a determined admin could patch out the
check or copy `instance.cfg`. Tamper-resistant enforcement requires the compiled
IP Core (plan Phase 3), where the license also derives the asset decryption key.
"""

import base64
import datetime
import json
import os
import re
import sys

# make bundled libs (rsa, pyasn1) importable
_LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

import rsa  # noqa: E402

_BIN = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_BIN)

# The app id IS the product id -- this file is identical in every Inno app.
PRODUCT = os.path.basename(_APP_DIR)
# A bundle key covers every app that lists itself in `products`.
BUNDLE_PRODUCT = "inno_suite"

_PUBKEY_PATH = os.path.join(_BIN, "license_pubkey.pem")

# 유예 기간 — 만료 후에도 앱이 계속 동작하는 일수.
# 정책(2026-07-26 사용자 결정): 차단은 전면적으로 하되 유예를 넉넉히 준다.
# 관측 도구라 갱신이 며칠 늦었다고 장애 대응 중에 화면이 꺼지면 안 되기 때문.
# 연간 구독 = 14일이 기본. 월간 키를 발급할 때는 payload 에 grace_days=3 을 명시해
# 덮어쓴다(payload 값이 항상 우선).
DEFAULT_GRACE_DAYS = 14
# states that warrant a notification; ordered by urgency
NOTIFY_STATES = ("d30", "d14", "d7", "d3", "d1", "grace", "stopped", "invalid")
DAILY_STATES = ("grace", "stopped")  # re-notify every day until resolved

# 라이선스가 "쓸 수 있는" 상태들. grace 포함 — 갱신이 며칠 늦었다고 장애 대응 중에
# 유료 기능이 꺼지면 안 된다.
USABLE_STATES = ("active", "d30", "d14", "d7", "d3", "d1", "grace")


# --------------------------------------------------------------------------- #
# editions / entitlements  (2026-07-30: 유료 전용 → 무료 배포 + 프리미엄 게이팅)
# --------------------------------------------------------------------------- #
#
# ⚠ 무료 티어에는 라이선스 키가 아예 없다 (키 미설정 = 정상 상태). 따라서 무료 한도는
#   payload 에서 올 수 없고 여기 상수가 정본이다. payload 의 `limits` 는 유료 키의
#   티어별 상한(예: 100 호스트 플랜)을 표현하기 위한 것이며, 없으면 무제한이다.
#
# 정책 결정 2026-07-30 (사용자): 무료 = 프리미엄 패널 게이팅 + 규모/기간 상한.
#   호스트 25 · 서비스 10 · 검색 7일. 우리 데모 환경(호스트 49 · 서비스 12)이
#   일부러 상한을 넘는 규모다 — 실제 생산 fleet 이면 유료 전환 지점에 닿는다.

FREE_EDITION = "free"
PAID_EDITION = "pro"          # payload 에 edition 이 없는 유료 키의 기본 표기
UNLIMITED = 0                 # ⚠ 0 = 무제한. None 은 "미지정"과 구별이 안 돼 쓰지 않는다.

# ⚠ 수량 상한(호스트/서비스/보존일) 개념은 2026-08-02 에 **제거**했다.
#    이유: 판매 단위가 "유료 에디션 하나"로 정해졌고, 무료 티어는 수량이 아니라
#    **프리미엄 기능 유무**로만 구분한다(🆓 대원칙). 상한은 문서에만 있고 화면·코드
#    어디에서도 적용된 적이 없었다 — 지키지 않는 약속을 코드에 남겨두면 다음 사람이
#    "이미 동작한다"고 믿게 된다.
#    되살릴 일이 생기면 payload 의 `limits` 를 다시 읽는 것부터 시작하면 된다
#    (발급 도구 tools/inno_mint_license.py 의 --limits 는 그대로 두었다).

# 프리미엄 기능 이름 — **이 튜플이 정본**이다. JS(apm_gate.js)·렌더 커맨드가 같은
# 문자열을 쓰므로 한쪽만 고치면 게이트가 조용히 어긋난다(상태 어휘 1:1 규약과 동일).
#   servicemap     Overview · Service Detail 의 서비스 토폴로지
#   scatter        Overview · Trace List 의 X-View 산점도
#   fleetmap       Infrastructure 의 Fleet Map (허니컴)
#   serverlist     Infrastructure 의 서버 목록
#   classification Classification Admin · Category Settings (관리자 CRUD)
#   studio         Chart Studio (inno_dashboard_studio)
#   agent          Agent 컬렉션 전체 (fleet · inventory · detail · deploy)   ← 2026-07-30 추가
#   events         System Events (apm_events)                              ← 2026-07-30 추가
#
# ⚠ 게이팅 방식이 기능마다 다르다(apm_gate.js 가 뷰별로 분기):
#   ① 패널 데모   무료 뷰 안의 프리미엄 패널만 예시로 (fleetmap)
#   ② 뷰 차단     화면 자체를 못 씀 (classification · studio)
#   ③ 샘플 모드   화면은 열리고 **전 패널이 테스트 데이터**, 클릭 이동도 그대로 (agent · events)
#      — 사용자 지정 2026-07-30. ②처럼 막지 않는 이유는 이 화면들이 제품의 핵심 데모 가치이기 때문.
PREMIUM_FEATURES = (
    "servicemap", "scatter", "fleetmap", "serverlist", "classification", "studio",
    "agent", "events",
    # rca = AI 근본원인분석 (2026-08-01 사용자 지정으로 유료화).
    # ⚠ 이전엔 서비스맵이 프리미엄이라 **간접적으로만** 막혀 있었다 — RCA 만 빼고 판 키나
    #   RCA 를 다른 화면에서 여는 경로가 생기면 그 판정이 조용히 어긋난다. 정식 항목으로 올린다.
    "rca",
)

# 미등록 배포 유예 — 노드락이 안 맞는 새 배포를 처음 본 뒤 N일간은 유료로 동작시킨다.
# 이유(계획서 11): DR 전환·하드웨어 교체로 manager_guid 가 바뀌면 고객은 야간에
# 아무 잘못 없이 막힌다. 키 재발급까지 걸리는 시간을 벌어준다.
#
# 🔴 2026-08-01 정책 변경 — 발급되는 키는 이제 payload 에 instance_grace_days=0 을
#   **항상 명시**한다(tools/inno_mint_license.py 기본값). 따라서 아래 상수는 그 필드가
#   없는 키, 즉 **정책 변경 이전에 발급된 키와 손으로 만든 키에만** 적용된다.
#
#   왜 0 이 기본이 됐나: 이 유예는 "잠기지 않은 Splunk 에서도 N일 프리미엄이 돈다"는
#   뜻이고, 창의 시작일은 아래 instances.json 에 있다 —
#   $SPLUNK_HOME/var/lib/splunk/modinputs/<app>/ 이라 **admin 이 지울 수 있다**.
#   지우면 창이 다시 시작되므로 유예는 선의의 재설치는 막아도 **의도적인 키 공유는
#   막지 못한다**. 방어는 로컬 상태가 아니라 서명된 payload 안에 있어야 한다 →
#   DR·하드웨어 교체는 유예가 아니라 **다중 GUID 락**으로 해결한다(발급 시 운영+DR).
#
#   ⚠ 이 값을 0 으로 바꾸지 말 것 — 구 키를 쓰는 고객이 DR 전환 시 즉시 멈춘다.
#      새 키는 어차피 payload 값(0)이 우선하므로 이 상수를 낮출 실익이 없다.
DEFAULT_INSTANCE_GRACE_DAYS = 14




def entitlements(status, state=None, days_remaining=None):
    """Single source of truth for what this deployment may do. Never raises.

    Everything user-facing -- the gate JS, the render commands, the license view --
    must branch on this and nothing else, so that "is premium on?" has exactly one
    answer in the product.

    Returns:
      tier        "paid" | "free"
      edition     payload edition, or "free"
      premium     bool -- premium panels render real data
      features    allowed premium feature names (list)
      limits      {hosts, services, retention_days}; 0 = unlimited
      state       subscription state (active/d30/.../grace/stopped/invalid)
      downgraded  bool -- a key IS installed but unusable, so we fell back to free

    ⚠ An unusable key does NOT block the app any more; it degrades to the free tier
      (`downgraded=True`). Blocking a whole observability UI because a renewal was
      late contradicts free distribution, and the previous all-or-nothing behaviour
      existed only because there was no free tier to fall back to.
    """
    if state is None:
        state, days_remaining = subscription_state(status)

    paid = state in USABLE_STATES
    has_key = bool(status.get("reason_code") and status.get("reason_code") != "no_key")

    if paid:
        edition = status.get("edition") or PAID_EDITION
        payload_features = status.get("features") or []
        # 빈 목록 = 전 기능 (has_feature 와 동일 규약). ⚠ PREMIUM_FEATURES 와 교집합을
        # 내면 안 된다 — payload 에는 프리미엄 목록에 없는 기능명(예 "rca")도 올 수 있고,
        # 그걸 걸러내면 그 기능이 조용히 거부된다(실제로 한 번 그렇게 깨뜨렸다).
        # 기능 판정의 권위는 언제나 has_feature() 이고, 이 목록은 표시용이다.
        features = list(payload_features) if payload_features else list(PREMIUM_FEATURES)
        return {
            "tier": "paid",
            "wm": status.get("wm"),
            "edition": edition,
            "premium": True,
            "features": features,
            "state": state,
            "days_remaining": days_remaining,
            "downgraded": False,
        }

    return {
        "tier": "free",
        "wm": None,          # 무료는 키가 없으니 워터마크도 없다
        "edition": FREE_EDITION,
        "premium": False,
        "features": [],
        "state": state,
        "days_remaining": days_remaining,
        "downgraded": has_key,
    }


def limit_exceeded(limits, key, observed):
    """True if `observed` breaks the limit. 0/None limit = unlimited.

    ⚠ Honest scope: for FREE core panels this is advisory -- the dashboard SPL is
      plaintext, so a determined admin can edit the cap out. Hard enforcement only
      exists where the SERVER builds the pipeline (the premium render commands).
      Every breach is still recorded in license_status, which is the audit lever.
    """
    try:
        cap = int(limits.get(key) or 0)
        obs = int(observed or 0)
    except Exception:
        return False
    return cap > 0 and obs > cap


# --------------------------------------------------------------------------- #
# encoding helpers
# --------------------------------------------------------------------------- #

def _b64url_decode(s):
    s = s.encode() if isinstance(s, str) else s
    return base64.urlsafe_b64decode(s + b"=" * (-len(s) % 4))


def b64url_encode(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _normalize_ids(value):
    """None / 'a,b' / ['a','b'] -> sorted unique UPPERCASE list of non-empty strings.

    Splunk reports GUIDs uppercase; uppercasing here makes matching case-insensitive
    so a hand-typed lowercase lock value still works.
    """
    if not value:
        return []
    items = value.split(",") if isinstance(value, str) else list(value)
    return sorted({str(a).strip().upper() for a in items if str(a).strip()})


def instance_allowed(locked_ids, current_id):
    """True if current_id satisfies the lock. Empty lock list = unrestricted.

    Mirrors `account_allowed()` in the S3 add-on so the two products stay
    conceptually identical.
    """
    locks = _normalize_ids(locked_ids)
    return (not locks) or (str(current_id or "").strip().upper() in locks)


# --------------------------------------------------------------------------- #
# instance identity (node-lock anchor + audit evidence)
# --------------------------------------------------------------------------- #

_IDENTITY_FIELDS = (
    "guid", "manager_guid", "serverName", "host_fqdn", "product_type",
    # ⚠ Cloud 판별은 product_type 이 아니라 instance_type 이다 — Splunk Cloud 에서도
    #   product_type 은 "enterprise" 이고 instance_type 만 "cloud" 로 온다
    #   (2026-07-27 amore.splunkcloud.com 실측).
    "instance_type",
    "version", "licenseKeys", "license_labels", "isTrial", "isFree",
)


def _splunk_home():
    home = os.environ.get("SPLUNK_HOME")
    if home:
        return home
    # <SPLUNK_HOME>/etc/apps/<app>/bin/ -> up four
    return os.path.dirname(os.path.dirname(os.path.dirname(_APP_DIR)))


def _conf_value(path, stanza, key):
    """Minimal .conf reader -- returns the last value of `key` inside `stanza`."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        return None
    current, found = None, None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            continue
        if current == stanza and "=" in line:
            k, _, v = line.partition("=")
            if k.strip() == key:
                found = v.strip()
    return found


def _mgmt_hostport():
    """Management URI. Host is pinned to loopback on purpose -- see _rest_identity."""
    home = _splunk_home()
    port = "8089"
    for conf in ("local", "default"):
        val = _conf_value(os.path.join(home, "etc", "system", conf, "web.conf"),
                          "settings", "mgmtHostPort")
        if val:
            m = re.search(r":(\d+)\s*$", val)
            if m:
                port = m.group(1)
                break
    return "127.0.0.1", port


def _rest_get(path, session_key):
    """GET a splunkd REST path as JSON. Returns the parsed doc or None; never raises.

    The host is hard-coded to 127.0.0.1 and is never configurable, so certificate
    verification is skipped only for splunkd's own self-signed loopback listener;
    no request can be redirected off-box.
    """
    if not session_key:
        return None
    try:
        import ssl
        from urllib.request import Request, urlopen

        host, port = _mgmt_hostport()
        sep = "&" if "?" in path else "?"
        url = "https://%s:%s%s%soutput_mode=json" % (host, port, path, sep)
        req = Request(url, headers={"Authorization": "Splunk %s" % session_key})
        ctx = ssl._create_unverified_context()  # loopback self-signed cert only
        with urlopen(req, timeout=10, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def _rest_identity(session_key):
    """Read /services/server/info over splunkd REST. Returns dict or None.

    Measured 2026-07-26: this endpoint's ACL is perms.read=["*"], so it needs no
    special capability and works for non-admin dashboard users. /services/licenser/*
    is admin-only, which is why nothing here depends on it.
    """
    doc = _rest_get("/services/server/info", session_key)
    if not doc:
        return None
    content = (doc.get("entry") or [{}])[0].get("content") or {}
    ident = {k: content.get(k) for k in _IDENTITY_FIELDS}
    # 10.x renamed master_guid -> manager_guid; accept either.
    if not ident.get("manager_guid"):
        ident["manager_guid"] = content.get("master_guid")
    ident["source"] = "rest"
    # Remember it for the disk fallback — on a license peer this is the only way the
    # anchor can be known without REST (see _disk_identity).
    _mgr_cache_write(ident.get("manager_guid"))
    return ident


def _mgr_cache_path():
    """Where the last REST-resolved manager_guid is remembered.

    Same tree as the modular input's instances.json so operators have one place
    to look (and one place to clear when they intentionally re-home a server).
    """
    return os.path.join(_splunk_home(), "var", "lib", "splunk", "modinputs",
                        PRODUCT, "manager_guid.txt")


def _mgr_cache_write(guid):
    """Best effort. A failure here must never break license verification."""
    if not guid:
        return
    try:
        path = _mgr_cache_path()
        d = os.path.dirname(path)
        if not os.path.isdir(d):
            os.makedirs(d)
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(guid).strip())
    except Exception:
        pass


def _mgr_cache_read():
    try:
        with open(_mgr_cache_path(), "r", encoding="utf-8") as f:
            return (f.read() or "").strip() or None
    except Exception:
        return None


_MGR_LOG_RE = re.compile(r"setting masterGuid='([0-9A-Fa-f-]{36})'")


def _mgr_from_splunkd_log(tail_bytes=262144):
    """Last resort: read the GUID Splunk itself recorded for its license manager.

    `LMTracker - setting masterGuid='<guid>'` is written on every startup, which is
    exactly the window where REST is not answering yet -- so this covers the gap the
    cache cannot (a peer that has never had a successful REST call).

    Bounded tail read: the file is hundreds of MB on busy servers and this runs on
    the license path, so it must stay cheap. Rotated files are deliberately not
    scanned -- if it is not in the current log, the cache above is the answer.
    """
    try:
        path = os.path.join(_splunk_home(), "var", "log", "splunk", "splunkd.log")
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            if size > tail_bytes:
                f.seek(size - tail_bytes)
            blob = f.read().decode("utf-8", "replace")
    except Exception:
        return None
    hits = _MGR_LOG_RE.findall(blob)
    return hits[-1] if hits else None


def _disk_identity():
    """Fallback when no session key is available (CLI, early startup).

    `instance.cfg` gives the instance GUID. If this instance is its own license
    manager (`manager_uri` absent or 'self') then manager_guid == guid, which is
    the case for every standalone deployment.
    """
    home = _splunk_home()
    ident = {k: None for k in _IDENTITY_FIELDS}
    ident["source"] = "disk"
    ident["guid"] = _conf_value(os.path.join(home, "etc", "instance.cfg"), "general", "guid")

    manager_uri = None
    for conf in ("local", "default"):
        path = os.path.join(home, "etc", "system", conf, "server.conf")
        manager_uri = (_conf_value(path, "license", "manager_uri")
                       or _conf_value(path, "license", "master_uri"))
        if manager_uri:
            break
    if not manager_uri or manager_uri.strip().lower() == "self":
        ident["manager_guid"] = ident["guid"]
        ident["manager_guid_source"] = "self"
    else:
        # 🔴 LICENSE PEER (every SHC member, indexer and extra search head).
        #    The manager's GUID is NOT in this host's conf, so before 2026-09-04 this
        #    branch left manager_guid = None -- and `instance_allowed()` turns None into
        #    `"" in locks` = False, i.e. a **paying customer got instance_mismatch**
        #    ("이 라이선스는 다른 Splunk 배포에 발급되었습니다") the moment REST was
        #    unavailable. Measured on a real 3-member SHC (samsung-shc, 2026-09-04):
        #    all members carry manager_uri and none can name the manager from conf alone.
        #    ⚠ Standalone deployments never hit this branch, which is why it went unseen.
        cached = _mgr_cache_read()
        if cached:
            ident["manager_guid"] = cached
            ident["manager_guid_source"] = "cache"
        else:
            logged = _mgr_from_splunkd_log()
            if logged:
                ident["manager_guid"] = logged
                ident["manager_guid_source"] = "splunkd.log"

    ident["serverName"] = _conf_value(
        os.path.join(home, "etc", "system", "local", "server.conf"), "general", "serverName")
    return ident


def instance_identity(session_key=None):
    """Resolve this deployment's identity. Never raises.

    Returns every field in _IDENTITY_FIELDS plus `source`. `manager_guid` is the
    node-lock anchor; the rest is audit evidence recorded in license_status events
    so that one key appearing at two different sites shows up as a mismatch in the
    corroborating fields (serverName was measured to drift from host_fqdn, so no
    single identifier is trusted on its own).
    """
    return _rest_identity(session_key) or _disk_identity()


# --------------------------------------------------------------------------- #
# verification
# --------------------------------------------------------------------------- #

def _load_pubkey(path=None):
    with open(path or _PUBKEY_PATH, "rb") as f:
        return rsa.PublicKey.load_pkcs1(f.read())


def _product_matches(payload):
    """Accept a single-product key, a bundle key, or a multi-product key."""
    products = payload.get("products")
    if products:
        return PRODUCT in _norm_products(products)
    product = payload.get("product")
    return product == PRODUCT or product == BUNDLE_PRODUCT


def _norm_products(value):
    items = value.split(",") if isinstance(value, str) else list(value or [])
    return {str(p).strip() for p in items if str(p).strip()}


def verify_license(key_str, identity=None, session_key=None, pubkey_path=None):
    """Return a status dict; never raises.

    `identity` may be supplied by the caller (avoids a REST round-trip when the
    caller already resolved it); otherwise it is resolved here.

    Returns keys: valid, reason, reason_code, customer, expiry, edition, features,
    splunk_manager_guid, splunk_guid, grace_days, provisional, days_remaining,
    identity.

    `reason_code` is the machine-readable counterpart of `reason` -- callers must
    branch on it rather than on the human text (the S3 version string-matched
    "expired", which breaks the moment the wording is localized).
    """
    result = {
        "valid": False,
        "customer": None,
        "expiry": None,
        "edition": None,
        "features": [],
        "splunk_manager_guid": [],
        "splunk_guid": [],
        "grace_days": None,
        "provisional": False,
        "days_remaining": None,
        "reason": "",
        "reason_code": "",
        "identity": identity,
        "instance_grace_days": None,
        "akey": None,
        "akeys": None,
        "wm": None,
    }

    if not key_str or not str(key_str).strip():
        result["reason"] = "라이선스 키가 설정되지 않았습니다. 설정 화면에서 키를 입력하세요."
        result["reason_code"] = "no_key"
        return result

    try:
        b64_payload, b64_sig = str(key_str).strip().split(".", 1)
        payload_bytes = _b64url_decode(b64_payload)
        signature = _b64url_decode(b64_sig)
    except Exception:
        result["reason"] = "라이선스 키 형식이 올바르지 않습니다."
        result["reason_code"] = "malformed"
        return result

    try:
        rsa.verify(payload_bytes, signature, _load_pubkey(pubkey_path))
    except Exception:
        result["reason"] = "라이선스 서명이 유효하지 않습니다 (변조되었거나 발급처가 불명확합니다)."
        result["reason_code"] = "bad_signature"
        return result

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        result["reason"] = "라이선스 내용을 읽을 수 없습니다."
        result["reason_code"] = "bad_payload"
        return result

    if not _product_matches(payload):
        result["reason"] = "다른 제품용 라이선스입니다."
        result["reason_code"] = "wrong_product"
        return result

    result["customer"] = payload.get("customer")
    result["expiry"] = payload.get("expiry")
    result["edition"] = payload.get("edition")
    result["features"] = payload.get("features") or []
    result["splunk_manager_guid"] = _normalize_ids(payload.get("splunk_manager_guid"))
    result["splunk_guid"] = _normalize_ids(payload.get("splunk_guid"))
    result["grace_days"] = payload.get("grace_days")
    # Refund-window (provisional) key: short expiry on purpose; surfaced so the UI
    # can explain it instead of alarming the customer.
    result["provisional"] = bool(payload.get("provisional"))
    # Tiered paid plans (e.g. a 100-host plan). Absent = unlimited, which is what
    # every key issued before 2026-07-30 means.
    result["instance_grace_days"] = payload.get("instance_grace_days")
    # 프리미엄 자산 복호화 키. ⚠ 2026-07-31 자산 번들 제거로 **현재 소비처가 없다** —
    # 키에 실려 와도 무시된다. 파싱만 남겨둔 이유는 구 키와의 호환(무해) + 번들 부활 시 재사용.
    # 서명된 payload 안에 있으므로
    # 위조·편집된 라이선스는 키를 공급할 수 없다.
    # 🔒 이 두 필드는 **절대 브라우저로 나가면 안 된다** — innolicense.py 의 FIELDS
    #    화이트리스트가 방어선이고, 하니스가 유출 없음을 검증한다. 새 필드를 노출할
    #    때 화이트리스트를 우회하지 말 것.
    result["akey"] = payload.get("akey")
    result["akeys"] = payload.get("akeys")
    # 워터마크 = 발급 원장 id. 프리미엄 산출물에 실어 **유출 시 출처를 특정**한다(계획서 §8).
    # ⚠ 비밀이 아니다(원장 조회용 식별자). 브라우저로 나가도 무방하며, 오히려 나가야 추적이 된다.
    result["wm"] = payload.get("wm")

    expiry = payload.get("expiry")
    if expiry:
        try:
            expiry_date = datetime.date.fromisoformat(expiry)
        except Exception:
            result["reason"] = "라이선스 만료일이 올바르지 않습니다."
            result["reason_code"] = "bad_expiry"
            return result
        result["days_remaining"] = (expiry_date - datetime.date.today()).days
        if datetime.date.today() > expiry_date:
            result["reason"] = "라이선스가 %s 에 만료되었습니다." % expiry
            result["reason_code"] = "expired"
            return result

    # node-lock last: an expired key should say "expired", not "wrong instance"
    if result["splunk_manager_guid"] or result["splunk_guid"]:
        if identity is None:
            identity = instance_identity(session_key)
            result["identity"] = identity
        # 🔴 "모른다" 를 "틀렸다" 로 단정하지 않는다.
        #    instance_allowed() 는 None 을 빈 문자열로 바꿔 비교하므로, anchor 를 못 읽으면
        #    자동으로 **불일치**가 된다 — 정품 고객에게 "다른 배포에 발급된 키" 라고 말하는 셈이다.
        #    라이선스 피어(SHC 멤버 등)에서 REST 가 잠깐 안 될 때 실제로 그렇게 됐다.
        #    사실대로 "확인 불가" 로 낸다. 프리미엄은 어차피 열리지 않으므로(valid=False)
        #    우회로가 열리는 것도 아니고, 다음 조회가 성공하면 저절로 회복된다.
        if result["splunk_manager_guid"] and not identity.get("manager_guid"):
            result["reason"] = (
                "이 배포의 ID 를 확인할 수 없어 라이선스를 대조하지 못했습니다. "
                "잠시 후 다시 시도하세요.")
            result["reason_code"] = "identity_unknown"
            return result
        ok = instance_allowed(result["splunk_manager_guid"], identity.get("manager_guid"))
        if ok and result["splunk_guid"]:
            ok = instance_allowed(result["splunk_guid"], identity.get("guid"))
        if not ok:
            result["reason"] = (
                "이 라이선스는 다른 Splunk 배포에 발급되었습니다 "
                "(현재 배포 ID %s). 이 배포용 키를 발급받으세요."
                % (identity.get("manager_guid") or identity.get("guid") or "unknown"))
            result["reason_code"] = "instance_mismatch"
            return result
    elif result["identity"] is None:
        result["identity"] = identity if identity is not None else instance_identity(session_key)

    result["valid"] = True
    result["reason"] = "ok"
    result["reason_code"] = "ok"
    return result


# --------------------------------------------------------------------------- #
# subscription state (unchanged semantics from the S3 add-on)
# --------------------------------------------------------------------------- #

def subscription_state(status, today=None):
    """Map a verify_license() result to a subscription state + days-to-expiry.

    Returns (state, days_remaining). Honors grace_days for the expired window.
      active            valid, >30 days left (or perpetual: days=None)
      d30/d14/d7/d3/d1  valid, expiring within N days
      grace             expiry passed but within grace_days (still working)
      stopped           past expiry + grace
      invalid           bad signature / product / node-lock / format
    """
    today = today or datetime.date.today()
    if not status.get("valid") and status.get("reason_code") != "expired":
        return "invalid", status.get("days_remaining")
    expiry = status.get("expiry")
    if not expiry:
        return "active", None  # perpetual
    try:
        exp = datetime.date.fromisoformat(expiry)
    except Exception:
        return "invalid", None
    dr = (exp - today).days
    if dr < 0:
        grace = status.get("grace_days")
        grace = DEFAULT_GRACE_DAYS if grace is None else int(grace)
        if today <= exp + datetime.timedelta(days=grace):
            return "grace", dr
        return "stopped", dr
    for thr, label in ((1, "d1"), (3, "d3"), (7, "d7"), (14, "d14"), (30, "d30")):
        if dr <= thr:
            return label, dr
    return "active", dr


def should_notify(state, last_state, last_date, today=None):
    """De-dupe: notify on entering a notify-state, or daily while grace/stopped."""
    today = (today or datetime.date.today()).isoformat()
    if state not in NOTIFY_STATES:
        return False
    if state != last_state:
        return True
    if state in DAILY_STATES and last_date != today:
        return True
    return False


# --------------------------------------------------------------------------- #
# license key storage
# --------------------------------------------------------------------------- #

KEY_REALM = PRODUCT
KEY_USER = "license_key"
KEY_CONF = "inno_license"  # <app>/{local,default}/inno_license.conf [license] key


def read_license_key(session_key=None):
    """Resolve the configured license key. Returns (key, source); never raises.

    Order: local/ conf -> default/ conf -> storage/passwords.

    CONF FIRST IS DELIBERATE. The gate runs inside a custom search command, whose
    session key belongs to the INVOKING USER, and the default `user` role has no
    `list_storage_passwords` capability (measured 2026-07-26). A conf file is read
    off disk by the splunkd-spawned process, so every context -- privileged modular
    input and unprivileged dashboard user alike -- resolves the SAME key and cannot
    disagree about license state. Reversing this order would make the gate fail for
    non-admins while the monitor reported "active", which is the worst possible
    support case.

    Casual REST reads of the conf are restricted by the metadata ACL; the key itself
    is a signed, node-locked token, so reading it grants nothing (it cannot be
    altered, and it will not validate on another deployment).

    storage/passwords stays as a secondary source for a UCC-style setup that writes
    there. `source` is surfaced so any divergence is visible instead of silent.
    """
    for scope in ("local", "default"):
        val = _conf_value(os.path.join(_APP_DIR, scope, KEY_CONF + ".conf"), "license", "key")
        if val:
            return val.strip(), "conf:%s" % scope

    doc = _rest_get("/servicesNS/nobody/%s/storage/passwords?count=0" % PRODUCT, session_key)
    for entry in (doc or {}).get("entry") or []:
        content = entry.get("content") or {}
        if content.get("realm") == KEY_REALM and content.get("username") == KEY_USER:
            secret = content.get("clear_password")
            if secret:
                return secret.strip(), "storage/passwords"
    return "", "unset"


def instance_first_seen(state_dir, manager_guid, today=None):
    """Record/return the date this deployment id was first observed.

    Returns (first_seen_iso, days_since, is_new). Used for the "unregistered instance"
    grace window and, more importantly, as DETECTION: a key surfacing on a deployment
    id we have never seen before is exactly the partner-redistribution signature, and
    it lands in the license_status event with a date attached.

    NOTE: the grace window itself is NOT applied here -- the length N is still an open
    policy decision (plan 11). This only produces the evidence needed to set it.
    """
    today = today or datetime.date.today()
    key = str(manager_guid or "unknown").upper()
    path = os.path.join(state_dir or "", "instances.json")
    seen = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            seen = json.load(f) or {}
    except Exception:
        seen = {}

    is_new = key not in seen
    if is_new:
        seen[key] = today.isoformat()
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(seen, f)
        except Exception:
            pass  # read-only checkpoint dir must never break the input

    first = seen.get(key) or today.isoformat()
    try:
        days = (today - datetime.date.fromisoformat(first)).days
    except Exception:
        days = 0
    return first, days, is_new


def apply_instance_grace(status, state_dir, today=None):
    """Let an otherwise-good key run for N days on a deployment it is not locked to.

    Solves the real support case: DR failover or a hardware swap changes
    `manager_guid`, so a paying customer is suddenly on `instance_mismatch` at 3am
    through no fault of their own. This buys time to get a re-issued key.

    Mutates and returns `status`. Only ever RELAXES `instance_mismatch` -- every
    other failure (bad signature, wrong product, expired) is untouched, so this can
    never turn a forged or expired key into a working one.

    Adds:
      instance_grace       True when the relaxation was applied
      instance_first_seen  date this deployment id was first observed
      instance_age_days    days since then
      instance_grace_left  days of grace remaining

    ⚠ Deliberately keyed on FIRST OBSERVATION, not on today: reinstalling the app or
      moving the clock does not restart the window, because instances.json keeps the
      original date. It is one window per deployment id, then a hard stop.
    """
    if status.get("reason_code") != "instance_mismatch":
        return status

    today = today or datetime.date.today()
    ident = status.get("identity") or {}
    anchor = ident.get("manager_guid") or ident.get("guid")

    window = status.get("instance_grace_days")
    window = DEFAULT_INSTANCE_GRACE_DAYS if window is None else int(window)

    first, age, _is_new = instance_first_seen(state_dir, anchor, today)
    status["instance_first_seen"] = first
    status["instance_age_days"] = age
    status["instance_grace"] = False
    status["instance_grace_left"] = 0

    if window <= 0 or age > window:
        return status

    status["valid"] = True
    status["instance_grace"] = True
    status["instance_grace_left"] = window - age
    status["reason_code"] = "instance_grace"
    status["reason"] = (
        "이 라이선스는 다른 Splunk 배포(%s)에 발급되었습니다. "
        "새 배포로 인정해 %d일간만 동작합니다 — 그 안에 이 배포 ID 로 키를 재발급받으세요."
        % (anchor or "unknown", window - age))
    return status


# --------------------------------------------------------------------------- #
# consumers
# --------------------------------------------------------------------------- #

def has_feature(status, name):
    """Feature-flag gate (e.g. 'studio'). An empty feature list means 'all'."""
    if not status.get("valid"):
        return False
    features = status.get("features") or []
    return (not features) or (name in features)


def status_event(status, state=None, days_remaining=None):
    """Flatten a status into the license_status event payload.

    Records the FULL identity, not just the anchor: one key used at two sites shows
    up as a mismatch in the corroborating fields even though the anchor was copied.
    """
    if state is None:
        state, days_remaining = subscription_state(status)
    ident = status.get("identity") or {}
    ent = entitlements(status, state, days_remaining)
    event = {
        "product": PRODUCT,
        "state": state,
        "days_remaining": days_remaining,
        "valid": status.get("valid"),
        "reason": status.get("reason"),
        "reason_code": status.get("reason_code"),
        "customer": status.get("customer"),
        "edition": ent.get("edition"),
        "expiry": status.get("expiry"),
        "features": status.get("features"),
        "provisional": status.get("provisional"),
        "identity_source": ident.get("source"),
        # ── 무료/유료 전환(2026-07-30) 이후의 감사 필드 ──
        # tier/premium 은 "이 배포가 실제로 무엇을 쓰고 있었나"의 기록이다. 갱신 영업
        # 근거이자, 무료로 오래 쓰던 배포가 갑자기 유료가 되는(=키 공유) 패턴 탐지용.
        "tier": ent.get("tier"),
        "premium": ent.get("premium"),
        "downgraded": ent.get("downgraded"),
        # 미등록 배포 유예 — 이 세 필드가 파트너 재배포의 서명이다(§11 항목 #6).
        # 고객 Splunk 에 남는 감사 기록 — 어느 키가 어디서 돌았는지의 1차 증거
        "wm": status.get("wm"),
        "instance_grace": status.get("instance_grace"),
        "instance_first_seen": status.get("instance_first_seen"),
        "instance_age_days": status.get("instance_age_days"),
    }
    for k in _IDENTITY_FIELDS:
        event[k] = ident.get(k)
    return event
