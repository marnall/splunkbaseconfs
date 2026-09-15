# Inno Observability for Splunk
# Copyright (c) 2026 Inno Software. All rights reserved.
#
# PROPRIETARY AND CONFIDENTIAL. Licensed, not sold — use requires a valid
# license key from Inno Software. Copying, redistribution, or removal of
# this notice is prohibited. See LICENSE.txt in this package.
# support@innosw.net · https://innosw.net/observability/terms.html
"""
Shuttle command: `| innocore spec=<name>`

THE APP COMPUTES NOTHING HERE. This file forwards a request to the IP Core daemon on
loopback and hands the answer back to the dashboard verbatim. It is deliberately
small and boring -- the interesting code is compiled and lives outside the package,
which is the entire point of the IP Core (docs/ip-protection-and-licensing-plan.md §7).

    | innocore spec=ping
    | innocore spec=ping echo=hello

WHY HTTP TO 127.0.0.1 AND NOT A CHILD PROCESS
    AppInspect Cloud forbids `subprocess` in app code, so this cannot exec a binary.
    Loopback HTTP is the only channel available to a vetted app -- and loopback is
    explicitly the one URL family AppInspect allows. Hence the core is a resident
    daemon, not something we spawn.

FAIL BEHAVIOUR (contract with the dashboards -- do not change casually)
    Never raises, never returns a partial answer. Every failure path returns exactly
    one row with `available=0` and a `reason_code`, and the panel falls back to sample
    data. Decided 2026-08-01: a premium panel that errors into a blank box is worse
    than one that says "sample data", and a core that is merely not installed yet must
    not look like a product fault.

    reason_code values: core_down · core_timeout · core_error · core_forbidden
                        plus whatever the core itself reports (unset, expired,
                        instance_mismatch, bad_signature, feature_locked, ...)

⚠ THIS COMMAND IS NOT THE LICENSE GATE. `| innolicense` remains the gate that
  dashboards read at load time -- it answers even when the core is absent, which is
  what makes the sample-data fallback possible. This command only carries premium
  DATA. Never make a dashboard depend on this command to decide the tier.
"""

import json
import os
import socket
import time
import sys

_BIN = os.path.dirname(os.path.abspath(__file__))
_APP = os.path.dirname(_BIN)
for _p in (os.path.join(_APP, "lib"), _BIN):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:                                    # py3
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError
    from urllib.parse import urlencode
except ImportError:                     # pragma: no cover - py2 never ships here
    Request = urlopen = HTTPError = URLError = urlencode = None

from splunklib.searchcommands import (  # noqa: E402
    Configuration, GeneratingCommand, Option, dispatch,
)

# 서버 쪽 진단 로그. ⚠ 없어도 셔틀은 그대로 돈다(폴백 계약이 우선).
try:
    import inno_log as LOG
except Exception:                        # pragma: no cover
    class LOG(object):                   # type: ignore
        @staticmethod
        def info(*a, **k): pass
        warn = debug = error = info
        @staticmethod
        def exception(*a, **k): pass

CORE_CONF = "inno_core"          # <app>/local/inno_core.conf  [core] port/token/timeout
DEFAULT_PORT = 8809
DEFAULT_TIMEOUT = 30.0           # ⚠ 코어가 검색을 직접 돌리므로 "로컬 호출" 감각으로
                                 #   잡으면 안 된다 — 대기 시간의 대부분은 splunkd 의
                                 #   검색 시간이다(2026-08-01 실측: 8초는 짧아 타임아웃).

# Stable output contract -- dashboards depend on these names. Adding is safe.
FIELDS = ("spec_name", "available", "licensed", "reason", "reason_code",
          "spec", "customer", "wm", "anchor", "core_version", "member")


def _conf_value(path, stanza, key):
    """Minimal .conf reader. Mirrors inno_license._conf_value; kept local so this
    command has no import-time dependency on the license module."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            cur = None
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    cur = line[1:-1].strip()
                    continue
                if cur != stanza or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == key:
                    return v.strip()
    except Exception:
        pass
    return ""


def _core_settings():
    path = os.path.join(_APP, "local", CORE_CONF + ".conf")
    port = _conf_value(path, "core", "port")
    timeout = _conf_value(path, "core", "timeout")
    try:
        port = int(port)
    except (TypeError, ValueError):
        port = DEFAULT_PORT
    try:
        timeout = float(timeout)
    except (TypeError, ValueError):
        timeout = DEFAULT_TIMEOUT
    return port, timeout, _conf_value(path, "core", "token")


def _member_name():
    """이 행을 만든 검색헤드 이름.

    ⚠ **앱 쪽에서** 구한다. SH 클러스터에서 알아야 하는 것은 "코어가 없는 멤버가
      누구인가" 인데, 코어가 응답에 자기 호스트명을 실으면 정작 필요한 경우
      (available=0, 코어 미기동)에 빈 값이 된다 — 필요한 순간에만 없는 필드가 된다.
      값은 `splunk_server` 와 맞추기 위해 serverName 을 1순위로 쓴다.
    """
    home = os.environ.get("SPLUNK_HOME") or ""
    if home:
        v = _conf_value(os.path.join(home, "etc", "system", "local", "server.conf"),
                        "general", "serverName")
        if v:
            return v
    try:
        return socket.gethostname()
    except Exception:
        return ""


def _row(spec_name, available, licensed, reason, code, payload=None):
    p = payload or {}
    spec = p.get("spec")
    return {
        "spec_name": spec_name,
        "available": 1 if available else 0,
        "licensed": 1 if licensed else 0,
        "reason": reason or "",
        "reason_code": code or "",
        # The spec is re-serialised as a string: SPL fields are flat, and the browser
        # JSON.parse()s it. Keeping it opaque here is deliberate -- the app must have
        # no opinion about the shape of what the core computed.
        "spec": json.dumps(spec, ensure_ascii=False) if spec is not None else "",
        "customer": p.get("customer") or "",
        "wm": p.get("wm") or "",
        "anchor": p.get("anchor") or "",
        "core_version": p.get("version") or "",
        "member": _member_name(),
    }


@Configuration()
class InnoCoreCommand(GeneratingCommand):
    spec = Option(require=True)
    echo = Option(require=False)
    # ⚠ SPL 조각이 아니라 **원자값 csv**를 받는다(예 "web-01,db-02" / "*" / "__none__").
    #   앱이 SPL 을 조립하면 안 되고, 조각을 옵션으로 넘기면 중첩 따옴표로 깨진다.
    hosts = Option(require=False)
    # ⚠ 이름이 `cdef` 인 이유: `def` 는 Python 예약어라 클래스 속성으로 쓸 수 없다.
    #   base64url 로 인코딩된 차트 정의(타입·SPL·색·임계)를 코어에 그대로 넘긴다.
    cdef = Option(require=False)
    # 백그라운드 작업 이름(`spec=job job=<id>`). 저장검색이 이 한 줄로 판정을 코어에 맡긴다.
    #
    # 🔴 **`name` 이라고 부르면 안 된다.** splunklib 이 커맨드 이름으로 쓰는 예약 속성이라
    #    `@Configuration()` 이 클래스 속성을 덮어써 **옵션 등록이 조용히 사라진다**
    #    (options 딕셔너리에 없고 `self.name` 은 'innocore' 를 돌려준다).
    #    증상은 Splunk 의 "Unrecognized option: name=..." 이고, 커맨드가 통째로 파싱 거부된다.
    # ⚠ 실측 2026-08-16: 코어를 HTTP 로 직접 부르는 하니스는 이걸 못 잡았다 — 실화면에서 드러났다.
    #    그래서 아래 [옵션 계약] 검사를 하니스에 넣었다.
    job = Option(require=False)
    # 차트 카탈로그 식별자(`spec=chart id=<차트키>`) — 앱은 이 한 줄만 안다.
    id = Option(require=False)
    # 필터 바 원자값(`scope="wlf=a,b;podf=*"`). SPL 조각이 **아니다** — 조립은 코어가 한다.
    scope = Option(require=False)
    svc = Option(require=False)        # RCA 분석 대상 서비스(빈값 = 코어가 최악 서비스 선택)
    lang = Option(require=False)       # RCA 응답 언어 ko|en
    earliest = Option(require=False)
    latest = Option(require=False)
    # ── Agent 화면(spec=agent) ────────────────────────────────────────────
    # 패널 이름과 필터 값만 넘긴다. SPL 조립·필터 판정은 코어가 한다(spec_agent.go).
    # ⚠ 여기 등록을 빠뜨리면 Splunk 가 커맨드를 통째로 파싱 거부한다
    #   ("Unrecognized option: label=…") — J2 에서 실제로 그렇게 전 패널이 비었다.
    #   `name` 사고와 같은 유형이라 아래 [옵션 계약] 하니스가 이 목록을 감시한다.
    panel = Option(require=False)
    label = Option(require=False)      # KPI 캡션 = 필드명. 문구는 앱이 갖는다(i18n 대상)
    q = Option(require=False)          # 검색어(부분일치) — 코어가 host="*q*" 로 만든다
    env = Option(require=False)
    role = Option(require=False)
    state = Option(require=False)
    host = Option(require=False)       # 에이전트 상세의 대상 노드
    # ── System Events(spec=events) ───────────────────────────────────────
    envs = Option(require=False)       # 환경 csv (다중 선택)
    svcs = Option(require=False)       # 서비스 csv — 코어가 실행 host 로 해석한다
    ip = Option(require=False)
    entity = Option(require=False)
    # Trace List 상태 필터(all|ok|delay|slow|err). ⚠ agent 의 `state` 와 다른 축이라 이름을 나눈다.
    status = Option(require=False)
    # ── Trace View(spec=trace) ───────────────────────────────────────────
    trace = Option(require=False)      # 조회할 trace_id
    ips = Option(require=False)        # 브로커·DB 의 peer IP csv — 코어가 host 로 해석한다
    # ── Overview 주요 시그널(spec=overview_signals) ──────────────────────
    # 전일비 창 — 화면의 시간 선택에 따라 길이가 달라져 앱이 계산해 넘긴다.
    yearliest = Option(require=False)
    ylatest = Option(require=False)

    def generate(self):
        name = (self.spec or "").strip()
        t0 = time.time()
        try:
            row = self._call(name)
        except Exception as e:        # absolutely never propagate to the dashboard
            LOG.exception("core.call_failed", e, spec=name)
            row = _row(name, False, False,
                       "IP Core 호출 중 오류가 발생했습니다.", "core_error")
        # ⚠ 결과 로깅은 **한 곳에서만** 한다. _call 안의 분기마다 심으면 반드시 하나를
        #   빠뜨리고, 그 분기가 하필 고객이 만나는 분기가 된다.
        #   available=0(코어에 못 붙음) 과 licensed=0(코어는 살아 있는데 거부) 은
        #   조치가 다르므로 둘 다 남긴다 — 폴백 계약의 핵심 구분이다.
        ms = int((time.time() - t0) * 1000)
        lvl = LOG.info if row.get("available") and row.get("licensed") else LOG.warn
        lvl("core.call", spec=name, available=row.get("available"),
            licensed=row.get("licensed"), reason_code=row.get("reason_code"), ms=ms)

        # ── 행을 그대로 내보내는 spec (`spec=options`) ─────────────────────
        # 🔴 클래식 뷰의 드롭다운은 **Splunk 입력 위젯이 직접 돌리는 검색**이라, 결과 행이 곧
        #    선택지다. 스펙 봉투 한 행을 주면 선택지가 하나(그것도 내부 필드)가 된다.
        # ⚠ 계산이 아니라 **전송 포장을 벗기는 것**이다(셔틀은 여전히 계산하지 않는다).
        # ⚠ 라이선스가 없으면 아무 행도 내지 않는다 — 빈 드롭다운이 실데이터 유출보다 낫다.
        if name == "options":
            emitted, parse_err = 0, ""
            if str(row.get("available")) == "1" and str(row.get("licensed")) == "1":
                try:
                    spec = json.loads(row.get("spec") or "{}") or {}
                except Exception as e:
                    spec, parse_err = {}, str(e)[:120]
                for r in (spec.get("rows") or []):
                    emitted += 1
                    yield {k: ("" if v is None else v) for k, v in r.items()}
            # ⚠ 이 줄이 없으면 "행이 0개인 것"과 "언랩이 깨진 것"을 구분할 수 없다 —
            #   드롭다운은 둘 다 빈 목록으로 보인다(실측으로 한 번 헤맸다).
            LOG.info("core.options", id=self.id or "", rows=emitted, parse_err=parse_err,
                     spec_len=len(row.get("spec") or ""))
            return

        yield row

    def _session_key(self):
        """The INVOKING USER's key, forwarded so the core's search runs as them.

        ⚠ A premium panel must never let a viewer see hosts their role cannot search.
          The license decides WHETHER the panel renders; Splunk RBAC still decides
          WHAT is in it. Forwarding a privileged key here would quietly break that.
        """
        try:
            return self.metadata.searchinfo.session_key or ""
        except Exception:
            return ""

    def _call(self, name):
        port, timeout, token = _core_settings()
        query = {}
        for key in ("echo", "hosts", "earliest", "latest", "cdef", "svc", "lang", "job",
                    "id", "scope", "panel", "label", "q", "env", "role", "state", "host",
                    "envs", "svcs", "ip", "entity", "status", "trace", "ips", "yearliest", "ylatest"):
            val = getattr(self, key, None)
            if val:
                query[key] = val
        url = "http://127.0.0.1:%d/v1/spec/%s" % (port, name)
        if query:
            url += "?" + urlencode(query)

        req = Request(url)
        if token:
            req.add_header("X-Inno-Token", token)
        session_key = self._session_key()
        if session_key:
            req.add_header("X-Inno-Session", session_key)

        try:
            with urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            # 403 = token mismatch. Distinguished from "down" because the fix is
            # different (align inno_core.conf, not start the service).
            code = "core_forbidden" if e.code == 403 else "core_error"
            return _row(name, False, False,
                        "IP Core 가 요청을 거부했습니다 (HTTP %s)." % e.code, code)
        except socket.timeout:
            # ⚠ Python 3.10+ raises socket.timeout (== TimeoutError, an OSError) from
            #   urlopen's own timeout -- it is NOT a URLError. Without this branch a
            #   slow search is reported as "response could not be parsed", which sends
            #   the operator looking for a protocol bug instead of a slow query.
            #   Measured 2026-08-01 on the live host.
            return _row(name, False, False,
                        "IP Core 응답이 시간 내에 오지 않았습니다 (조회가 느립니다).",
                        "core_timeout")
        except URLError as e:
            reason = getattr(e, "reason", e)
            is_timeout = "timed out" in str(reason).lower()
            return _row(name, False, False,
                        "IP Core 에 연결할 수 없습니다. 설치·기동 상태를 확인하세요.",
                        "core_timeout" if is_timeout else "core_down")
        except Exception:
            return _row(name, False, False,
                        "IP Core 응답을 해석할 수 없습니다.", "core_error")

        if not body.get("ok"):
            return _row(name, False, False,
                        body.get("reason") or "IP Core 가 요청을 처리하지 못했습니다.",
                        body.get("reason_code") or "core_error", body)
        if not body.get("licensed"):
            # Reached the core, and the core said no. This is a LICENSE answer, not a
            # transport failure -- available=1 so the panel can show the real reason.
            return _row(name, True, False,
                        body.get("reason") or "", body.get("reason_code") or "", body)
        # 🔴 라이선스는 유효한데 **스펙을 못 만든** 경우(asset_locked·search_failed·unknown_spec)
        #    코어는 정확한 문장을 준다. 예전에는 여기서 "" 로 버려서 화면이 이유 없이 비었다
        #    (2026-08-20 실사고: 자산 키 세대 불일치로 전 패널이 asset_locked 였는데 빈 화면만 보였다).
        return _row(name, True, True, body.get("reason") or "",
                    body.get("reason_code") or "ok", body)


dispatch(InnoCoreCommand, sys.argv, sys.stdin, sys.stdout, __name__)
