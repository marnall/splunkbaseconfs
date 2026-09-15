# Inno Observability for Splunk
# Copyright (c) 2026 Inno Software. All rights reserved.
#
# PROPRIETARY AND CONFIDENTIAL. Licensed, not sold — use requires a valid
# license key from Inno Software. Copying, redistribution, or removal of
# this notice is prohibited. See LICENSE.txt in this package.
# support@innosw.net · https://innosw.net/observability/terms.html
"""
Custom generating search command: `| innolicense`

THE LICENSE GATE. Dashboards call this instead of checking a license in JavaScript,
because a JS check is decoration -- anyone can edit the file. A search command runs
server-side, returns STATUS ONLY, and never hands the key to the browser.

    | innolicense
    | innolicense feature=studio

Returns exactly one row (see FIELDS below). It never raises and never returns the
license key itself.

Why a search command rather than a REST handler (chosen 2026-07-26):
  * the default `user` role HAS `run_custom_command` but NOT `list_storage_passwords`
    (measured on the live instance), so a command works for ordinary dashboard users
    while a storage/passwords read would not;
  * it is the same shape as the Phase 3 plan, where dashboard SPL becomes `| inno_*`
    commands backed by the IP Core -- so this gate is not throwaway scaffolding.

Scope note: registered app-locally (no `export = system`). Both apps ship the same
command name, so exporting either one globally would collide.
"""

import datetime
import importlib.util
import os
import sys

_BIN = os.path.dirname(os.path.abspath(__file__))
_APP = os.path.dirname(_BIN)
for _p in (os.path.join(_APP, "lib"), _BIN):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

from splunklib.searchcommands import (  # noqa: E402
    Configuration, GeneratingCommand, Option, dispatch,
)

# 서버 쪽 진단 로그. ⚠ import 실패가 게이트를 깨면 안 된다 — 없으면 조용히 안 남긴다.
try:
    import inno_log as LOG  # noqa: E402
except Exception:           # pragma: no cover
    class LOG(object):      # type: ignore
        @staticmethod
        def info(*a, **k): pass
        warn = debug = error = info
        @staticmethod
        def exception(*a, **k): pass
        @staticmethod
        def short_id(v): return ""
        @staticmethod
        def log_file(): return ""


def _load_sibling(name):
    if name in sys.modules:
        return sys.modules[name]
    path = os.path.join(_BIN, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


L = _load_sibling("inno_license")

# Stable output contract -- dashboards and SPL depend on these names.
# ⚠ 이름을 바꾸거나 빼면 apm_gate.js·렌더 커맨드가 조용히 어긋난다. 추가는 안전.
def _asset_kids(status):
    """라이선스 payload 에 실린 자산 키 **세대 이름**만 돌려준다(값은 절대 안 나간다)."""
    try:
        return sorted(((status or {}).get("akeys") or {}).keys())
    except Exception:
        return []


FIELDS = (
    "product", "licensed", "state", "days_remaining", "customer", "edition",
    "expiry", "features", "feature", "feature_allowed", "reason", "reason_code",
    "consequence", "manager_guid", "guid", "serverName", "product_type",
    "instance_type",
    "key_source", "identity_source", "checked_at",
    # ── 무료 배포 + 프리미엄 게이팅 (2026-07-30) ──
    # tier/premium 이 화면이 실제로 분기하는 값이다. licensed 는 기존 의미를 그대로
    # 유지한다(유료 키가 쓸 수 있는 상태인가) — 무료 티어에서는 0 이지만 그게 정상이며
    # 더 이상 "차단"을 뜻하지 않는다.
    "tier", "premium", "downgraded",
    "instance_grace", "instance_grace_left", "instance_first_seen",
    # 워터마크(발급 원장 id) — 화면·산출물에 실려 유출 출처 특정에 쓰인다.
    "wm",
    # 🔴 자산 키 유무 (2026-08-20 사고 후 추가).
    #   자산 키가 없는 유료 키는 **검증은 통과하는데 프리미엄 패널이 하나도 안 열린다**
    #   (코어의 모든 spec 이 asset_locked). 그때 이 커맨드는 licensed=1 tier=paid 로
    #   멀쩡해 보였고, 그래서 원인을 키에서 찾을 수가 없었다. 이제 한 줄로 보인다.
    #   ⚠ 키 값 자체는 절대 내보내지 않는다 — kid(세대 이름)와 유무만.
    "assets", "asset_kids",
)


def _consequence(state, tier="free", downgraded=False):
    """무료 티어로 강등된 사유를 사람 말로. 전면차단 문구는 폐기됐다.

    ⚠ 예전 문구는 "앱이 동작을 멈췄습니다" 였다 — 무료 티어가 생긴 뒤로는 사실이
      아니다(코어 관측은 계속 돈다). 틀린 안내는 곧 지원 문의가 된다.
    """
    if tier == "paid":
        if state == "grace":
            return "라이선스 만료 — 유예 기간입니다. 이후 무료 티어로 전환됩니다."
        return ""
    if not downgraded:
        return ""  # 무료 티어를 그냥 쓰는 중 = 정상, 알릴 것 없음
    if state == "stopped":
        return "라이선스가 만료돼 무료 티어로 전환되었습니다. 갱신 키를 입력하면 즉시 복구됩니다."
    return "라이선스를 사용할 수 없어 무료 티어로 동작합니다."


def _state_dir():
    """Writable checkpoint dir for instances.json (deployment first-seen ledger).

    Same location the modular input uses, so the gate and the monitor agree on when
    a deployment id was first observed.
    """
    home = os.environ.get("SPLUNK_HOME") or ""
    if home:
        return os.path.join(home, "var", "lib", "splunk", "modinputs", L.PRODUCT)
    return os.path.join(_APP, "local")


def build_row(session_key=None, feature=None, today=None, state_dir=None):
    """Produce the single status row. Pure enough to test without splunkd.

    `tier`/`premium` are what dashboards branch on:
      tier=free  -> core observability renders, premium panels show a demo preview
      tier=paid  -> everything renders with real data

    `licensed` keeps its original meaning (a usable PAID key) for the callers that
    already read it; it is 0 on the free tier, which is now a normal state rather
    than a blocked one.
    """
    today = today or datetime.date.today()
    row = {k: None for k in FIELDS}
    row["product"] = L.PRODUCT
    row["feature"] = feature
    row["checked_at"] = datetime.datetime.now().isoformat(timespec="seconds")

    try:
        key, key_source = L.read_license_key(session_key)
        identity = L.instance_identity(session_key)
        status = L.verify_license(key, identity=identity)
        # ⚠ 유예는 subscription_state 앞에 적용해야 한다 — state 가 valid 를 읽기 때문에
        #   순서를 바꾸면 유예가 적용돼도 invalid 로 남는다.
        status = L.apply_instance_grace(status, state_dir or _state_dir(), today)
        state, days = L.subscription_state(status, today)
        ent = L.entitlements(status, state, days)
    except Exception as e:  # a broken check must not break every dashboard
        # ⚠ fail closed 는 "프리미엄에 대해서만" 이다. 게이트가 고장났다고 코어 관측까지
        #   끄면 관측 도구로서 최악이고, 무료 티어는 원래 키가 없어도 도는 티어다.
        # 원인을 서버 로그에 남긴다. 이게 없으면 고객 화면엔 "확인 실패" 만 뜨고
        # 우리는 물어볼 것이 없다(스택까지 남긴다 — 어디서 났는지가 진단의 전부다).
        LOG.exception("license.check_failed", e, feature=feature)
        row.update({
            "state": "invalid", "licensed": 0, "tier": "free", "premium": 0,
            "downgraded": 1, "feature_allowed": 0,
            "reason_code": "check_failed",
            "reason": "라이선스 확인에 실패했습니다: %s" % e,
            "consequence": "라이선스를 확인할 수 없어 무료 티어로 동작합니다.",
        })
        return row

    ident = status.get("identity") or {}
    row.update({
        "licensed": 1 if ent["tier"] == "paid" else 0,
        "tier": ent["tier"],
        "premium": 1 if ent["premium"] else 0,
        "downgraded": 1 if ent["downgraded"] else 0,
        "state": state,
        "days_remaining": days,
        "customer": status.get("customer"),
        "edition": ent["edition"],
        "expiry": status.get("expiry"),
        # 유료면 허용 프리미엄 기능 목록, 무료면 빈 문자열
        "features": ",".join(ent.get("features") or []),
        "reason": status.get("reason"),
        "reason_code": status.get("reason_code"),
        "consequence": _consequence(state, ent["tier"], ent["downgraded"]),
        "manager_guid": ident.get("manager_guid"),
        "guid": ident.get("guid"),
        "serverName": ident.get("serverName"),
        "product_type": ident.get("product_type"),
        "instance_type": ident.get("instance_type"),
        "key_source": key_source,
        "identity_source": ident.get("source"),
        "instance_grace": 1 if status.get("instance_grace") else 0,
        "instance_grace_left": status.get("instance_grace_left"),
        "instance_first_seen": status.get("instance_first_seen"),
        "wm": ent.get("wm"),
        "assets": 1 if _asset_kids(status) else 0,
        "asset_kids": ",".join(_asset_kids(status)),
    })
    # feature=<name> 은 "이 기능을 켜도 되나"를 묻는다.
    # ⚠ 판정은 반드시 L.has_feature — payload 의 빈 목록 = 전 기능 규약이 여기 들어있다.
    #   ent["features"] 로 판정하면 프리미엄 목록 밖의 기능명이 거부된다(회귀 경험).
    row["feature_allowed"] = (
        1 if (ent["premium"] and (not feature or L.has_feature(status, feature))) else 0
    )
    # 판정 결과 한 줄. 티어·사유·키 출처·유예 상태만 남긴다 — 키 자체는 절대 남기지 않고,
    # 배포 GUID 도 앞 8자만 남겨(대조는 되고 위조엔 못 쓴다) 노드락 문의를 좁힐 수 있게 한다.
    LOG.info("license.check",
             feature=feature, tier=row.get("tier"), state=row.get("state"),
             licensed=row.get("licensed"), premium=row.get("premium"),
             feature_allowed=row.get("feature_allowed"),
             reason_code=row.get("reason_code"), key_source=row.get("key_source"),
             identity_source=row.get("identity_source"),
             manager_guid8=LOG.short_id(row.get("manager_guid")),
             instance_grace=row.get("instance_grace"),
             instance_grace_left=row.get("instance_grace_left"))
    return row


@Configuration()
class InnoLicenseCommand(GeneratingCommand):
    """Emit one row describing this deployment's license state."""

    feature = Option(
        doc="Optional feature flag to test, e.g. feature=studio. Adds feature_allowed.",
        require=False,
    )

    def generate(self):
        try:
            session_key = self.metadata.searchinfo.session_key
        except Exception:
            session_key = None
        yield build_row(session_key, self.feature)


if __name__ == "__main__":
    dispatch(InnoLicenseCommand, sys.argv, sys.stdin, sys.stdout, __name__)
