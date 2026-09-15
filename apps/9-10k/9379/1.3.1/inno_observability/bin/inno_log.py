# -*- coding: utf-8 -*-
# Inno Observability for Splunk
# Copyright (c) 2026 Inno Software. All rights reserved.
#
# PROPRIETARY AND CONFIDENTIAL. Licensed, not sold — use requires a valid
# license key from Inno Software. Copying, redistribution, or removal of
# this notice is prohibited. See LICENSE.txt in this package.
# support@innosw.net · https://innosw.net/observability/terms.html
"""서버 쪽 진단 로그 — 앱의 Python 구성요소가 남기는 유일한 기록.

왜 있는가
    브라우저 쪽 기록(appserver/static/apm_log.js)은 화면이 무엇을 물어봤는지까지만 안다.
    "라이선스 커맨드가 왜 free 를 돌려줬는지", "IP Core 에 왜 못 붙었는지" 는 서버에서만
    알 수 있고, 지금까지 그 부분은 **아무 데도 안 남았다**. 고객이 "프리미엄이 안 열려요"
    라고 하면 우리가 물어볼 것이 없었다.

어디에 쓰는가
    `$SPLUNK_HOME/var/log/splunk/<app>.log`
    Splunk 가 이 디렉터리를 기본으로 모니터하므로 **별도 inputs.conf 없이** `_internal` 로
    들어간다. 즉 관리자가 검색 한 줄로 꺼낼 수 있다:
        index=_internal source=*inno_observability.log
    ⚠ `_internal` 은 일반 user 롤에 안 열려 있을 수 있다(srchIndexesAllowed=* 는 _* 를
      포함하지 않는다). 지원 절차는 관리자가 수행하는 것을 전제로 한다.

설계 원칙
    ① **절대 예외를 밖으로 내지 않는다.** 로깅이 제품을 멈추면 최악이다. 모든 진입점이
       try 로 감싸여 있고, 실패하면 그냥 조용히 아무것도 안 한다.
    ② **시크릿을 남기지 않는다.** 라이선스 키·HEC 토큰·서명은 기록 대상이 아니다.
       그래도 실수로 섞일 수 있으므로 내보내기 전에 한 번 더 지운다.
       ⚠ 배포 GUID 는 **지운다.** 노드락 진단에는 필요하지만, 지운 값 대신
       앞 8자만 남겨 같은 배포인지 대조할 수 있게 한다(원문이 있으면 키 위조에 쓰인다).
    ③ **한 줄 = 한 사건.** 검색으로 세고 묶을 수 있어야 하므로 key=value 로 쓴다.
"""

from __future__ import absolute_import

import logging
import logging.handlers
import os
import re
import sys
import time

_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.basename(_APP_DIR)          # 앱 디렉터리명 = 제품 id (사본에서도 자동으로 맞는다)

_MAX_BYTES = 5 * 1024 * 1024
_BACKUPS = 3
_logger = None

# 실수로 섞여 들어올 수 있는 값들. 완벽한 탐지는 불가능하므로 넉넉히 지운다 —
# 진단이 조금 덜 자세한 것보다 시크릿이 새는 쪽이 훨씬 나쁘다.
_SECRET = [
    re.compile(r"[A-Za-z0-9_\-]{40,}\.[A-Za-z0-9_\-]{40,}"),                 # 라이선스 키(payload.sig)
    re.compile(r"(?i)\b(token|key|password|secret|authorization)\s*[=:]\s*\S+"),
    re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
               r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"),                          # HEC 토큰·GUID 형태
]


def _log_path():
    home = os.environ.get("SPLUNK_HOME") or ""
    if home:
        d = os.path.join(home, "var", "log", "splunk")
        if os.path.isdir(d):
            return os.path.join(d, APP + ".log")
    # splunkd 밖에서 돌 때(하니스·개발) — 앱 안에 남긴다. 패키지엔 안 실린다(local/ 은 제외됨).
    d = os.path.join(_APP_DIR, "local")
    try:
        os.makedirs(d)
    except OSError:
        pass
    return os.path.join(d, APP + ".log")


def _get():
    global _logger
    if _logger is not None:
        return _logger
    lg = logging.getLogger("inno." + APP)
    lg.propagate = False                                  # splunkd 로그로 새어나가지 않게
    if not lg.handlers:
        try:
            h = logging.handlers.RotatingFileHandler(
                _log_path(), maxBytes=_MAX_BYTES, backupCount=_BACKUPS, encoding="utf-8")
            # ⚠ **반드시 UTC + 명시적 오프셋**으로 쓴다.
            #    splunkd 는 검색 커맨드를 **호출한 사용자의 시간대**로 띄운다 — admin 의
            #    Splunk 시간대가 Asia/Seoul 이면 UTC 서버인데도 로그가 KST 로 찍힌다.
            #    그러면 Splunk 는 그 시각을 서버 로컬(UTC)로 읽어 **9시간 미래**로 색인하고,
            #    관리자가 "최근 1시간" 으로 검색하면 **한 줄도 안 나온다**
            #    (2026-08-02 실측: 파일은 100% 읽혔는데 검색 결과 0건이었다).
            #    사용자마다 시간대가 다르면 같은 파일 안에서 시각이 뒤섞이기까지 한다.
            fmt = logging.Formatter(
                "%(asctime)s.%(msecs)03dZ %(levelname)s component=%(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S")
            fmt.converter = time.gmtime
            h.setFormatter(fmt)
            lg.addHandler(h)
        except Exception:
            lg.addHandler(logging.NullHandler())          # 못 쓰면 조용히 포기한다
    lg.setLevel(_level())
    _logger = lg
    return lg


def _level():
    """기본 INFO. 재현이 어려운 문제는 고객에게 DEBUG 로 올려 달라고 할 수 있어야 한다.

    ⚠ 환경변수가 아니라 conf 로 받는 이유 = splunkd 가 띄우는 프로세스에는 우리가 원하는
      환경변수를 넣을 방법이 없다. 관리자가 파일 한 줄만 고치면 되게 한다.
          $SPLUNK_HOME/etc/apps/<app>/local/inno_log.conf
          [logging]
          level = DEBUG
    """
    try:
        p = os.path.join(_APP_DIR, "local", "inno_log.conf")
        if os.path.exists(p):
            with open(p, "r") as f:
                for line in f:
                    m = re.match(r"\s*level\s*=\s*(\w+)", line)
                    if m:
                        return getattr(logging, m.group(1).upper(), logging.INFO)
    except Exception:
        pass
    return logging.INFO


def scrub(text):
    s = "" if text is None else str(text)
    for pat in _SECRET:
        s = pat.sub("<redacted>", s)
    return s


def short_id(value):
    """배포 GUID 처럼 대조는 필요하지만 원문을 남기면 안 되는 값 — 앞 8자만."""
    s = "" if value is None else str(value)
    return (s[:8] + "…") if len(s) > 8 else s


def _fmt(event, fields):
    parts = ["event=" + str(event)]
    for k in sorted(fields or {}):
        v = fields[k]
        if v is None:
            continue
        v = scrub(v)
        if re.search(r"\s", v):
            v = '"' + v.replace('"', "'") + '"'
        parts.append("%s=%s" % (k, v))
    return " ".join(parts)


def _emit(level, event, **fields):
    try:
        _get().log(level, _fmt(event, fields))
    except Exception:
        pass                                              # 로깅은 절대 호출자를 깨뜨리지 않는다


def debug(event, **f):
    _emit(logging.DEBUG, event, **f)


def info(event, **f):
    _emit(logging.INFO, event, **f)


def warn(event, **f):
    _emit(logging.WARNING, event, **f)


def error(event, **f):
    _emit(logging.ERROR, event, **f)


def exception(event, exc, **f):
    """예외는 한 줄 요약 + 스택을 함께 남긴다.

    스택이 없으면 "check_failed" 만 보이고 어디서 났는지 알 수 없어 진단이 거기서 끝난다.
    """
    try:
        import traceback
        f = dict(f or {})
        f["error"] = "%s: %s" % (type(exc).__name__, exc)
        _emit(logging.ERROR, event, **f)
        _get().error("event=%s.traceback\n%s" % (event, scrub(traceback.format_exc())))
    except Exception:
        pass


def log_file():
    """진단 화면이 "어디를 보면 되는지" 안내할 때 쓴다."""
    try:
        return _log_path()
    except Exception:
        return ""


def python_info():
    return "%d.%d.%d" % sys.version_info[:3]
