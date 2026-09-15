# Inno Observability for Splunk
# Copyright (c) 2026 Inno Software. All rights reserved.
#
# PROPRIETARY AND CONFIDENTIAL. Licensed, not sold — use requires a valid
# license key from Inno Software. Copying, redistribution, or removal of
# this notice is prohibited. See LICENSE.txt in this package.
# support@innosw.net · https://innosw.net/observability/terms.html
"""
Modular input: license state monitor.

Runs on an interval INSIDE Splunk (reliable clock, no external dependency). Each run:
  1. reads the configured license key,
  2. verifies it and computes the subscription state / days-to-expiry,
  3. records the deployment id it is running on (first-seen tracking),
  4. writes a `license_status` event so admins can dashboard and alert on it with
     ordinary Splunk alerting (`state!="active"`).

Customers are typically air-gapped, so this is LOCAL telemetry -- it never phones
home. Two audiences:
  * the customer: renewal countdown + their own alerting hook;
  * the vendor: the audit trail. The event carries the full instance identity
    (anchor + corroborating fields), so one key appearing on two different
    deployments shows up as a mismatch even if the anchor value was copied.
    See docs/ip-protection-and-licensing-plan.md 4/8.

Ported from the S3 add-on's `license_monitor.py`, but that version was built on UCC
(`splunklib.modularinput`, `solnlib.conf_manager`, `import_declare_test`). These apps
carry no UCC, so the modular-input protocol is implemented here directly on the
standard library -- it is a small, stable XML contract and avoids pulling the whole
Splunk SDK into the package for one input.
"""

import datetime
import importlib.util
import json
import os
import sys
import time
from xml.sax.saxutils import escape

SOURCETYPE = "inno:license"

# Never trust __file__/sys.path alone for sibling modules under splunkd: resolve bin/
# from SPLUNK_HOME too and load by explicit path (same lesson as the S3 add-on).


def _candidate_bins():
    cands = []
    try:
        cands.append(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        pass
    home = os.environ.get("SPLUNK_HOME")
    if home:
        app = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        cands.append(os.path.join(home, "etc", "apps", app, "bin"))
    out, seen = [], set()
    for c in cands:
        if c and c not in seen and os.path.isdir(c):
            seen.add(c)
            out.append(c)
    return out


def _load_sibling(name):
    if name in sys.modules:
        return sys.modules[name]
    for base in _candidate_bins():
        path = os.path.join(base, name + ".py")
        if os.path.isfile(path):
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
            return mod
    raise ImportError("cannot locate %s.py (bins=%s)" % (name, _candidate_bins()))


L = _load_sibling("inno_license")


# 앱 공용 진단 로그. 없으면 stderr 만 쓴다(동작에는 영향 없음).
try:
    LOG = _load_sibling("inno_log")
except Exception:                       # pragma: no cover
    LOG = None


def _log(level, msg):
    """splunkd captures a modular input's stderr into splunkd.log.

    stderr 만으로는 splunkd.log 에 섞여 우리 앱 기록만 뽑아내기 어렵다. 앱 전용 파일에도
    같이 남겨 지원 절차가 파일 하나만 보면 되게 한다.
    """
    sys.stderr.write("%s inno_license_monitor - %s\n" % (level, msg))
    sys.stderr.flush()
    if LOG is not None:
        try:
            {"ERROR": LOG.error, "WARN": LOG.warn}.get(level, LOG.info)(
                "monitor", detail=msg)
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# modular input protocol (stdin: input definition XML / stdout: event stream XML)
# --------------------------------------------------------------------------- #

# use_single_instance=false: the script emits once and exits, so splunkd must
# re-invoke it every `interval`. With true, splunkd treats it as one long-running
# process, logs "Ignoring parameter interval", and it runs only once at startup.
SCHEME = """<scheme>
  <title>Inno license monitor</title>
  <description>Writes periodic license_status events. The app stops working when the
  license expires (after the grace period).</description>
  <use_external_validation>false</use_external_validation>
  <use_single_instance>false</use_single_instance>
  <streaming_mode>xml</streaming_mode>
  <endpoint>
    <args>
      <arg name="name">
        <title>Name</title>
        <required_on_create>true</required_on_create>
      </arg>
    </args>
  </endpoint>
</scheme>
"""


def _parse_input_definition(raw):
    """Return (session_key, checkpoint_dir, [stanza names]). Never raises.

    Uses defusedxml when bundled; the payload comes from splunkd (trusted), but the
    hardened parser is preferred to keep AppInspect's XML checks satisfied.
    """
    try:
        try:
            from defusedxml.ElementTree import fromstring
        except ImportError:
            from xml.etree.ElementTree import fromstring
        root = fromstring(raw)
    except Exception as e:
        _log("ERROR", "could not parse input definition: %s" % e)
        return "", "", []

    def text(tag):
        node = root.find(tag)
        return (node.text or "").strip() if node is not None and node.text else ""

    stanzas = [s.get("name") for s in root.findall("./configuration/stanza")
               if s.get("name")]
    return text("session_key"), text("checkpoint_dir"), stanzas


def _emit(events):
    out = ["<stream>"]
    for source, data in events:
        out.append(
            "<event><time>%d</time><source>%s</source><sourcetype>%s</sourcetype>"
            "<data>%s</data></event>"
            % (int(time.time()), escape(source), escape(SOURCETYPE), escape(data))
        )
    out.append("</stream>")
    sys.stdout.write("".join(out))
    sys.stdout.flush()


# --------------------------------------------------------------------------- #
# the check
# --------------------------------------------------------------------------- #

def _consequence(state):
    if state == "stopped":
        return "라이선스 만료 — 앱이 동작을 멈췄습니다. 갱신 키를 입력하세요."
    if state == "grace":
        return "라이선스 만료 — 유예 기간에만 동작하며, 이후 중지됩니다."
    if state == "invalid":
        return "라이선스가 유효하지 않아 앱이 동작하지 않습니다."
    return "만료일 + 유예 기간이 지나면 앱이 동작을 멈춥니다."


def build_status(session_key, checkpoint_dir, today=None):
    """Verify + enrich into the event dict. Split out so tests can drive it."""
    today = today or datetime.date.today()
    key, key_source = L.read_license_key(session_key)
    identity = L.instance_identity(session_key)
    status = L.verify_license(key, identity=identity)
    state, days = L.subscription_state(status, today)

    event = L.status_event(status, state, days)
    event["consequence"] = _consequence(state)
    event["grace_days"] = status.get("grace_days")
    # surfaced so a monitor/gate disagreement about WHICH key was read is visible
    event["key_source"] = key_source

    # deployment first-seen: the partner-redistribution signature is a valid key
    # showing up on a deployment id we have never observed before.
    first, since, is_new = L.instance_first_seen(
        checkpoint_dir, identity.get("manager_guid"), today)
    event["instance_first_seen"] = first
    event["instance_days_known"] = since
    event["instance_is_new"] = is_new
    return event


def run(stdin_raw):
    session_key, checkpoint_dir, stanzas = _parse_input_definition(stdin_raw)
    try:
        event = build_status(session_key, checkpoint_dir)
    except Exception as e:
        _log("ERROR", "license check failed: %s" % e)
        return 1

    if event.get("state") != "active":
        _log("WARN", "license state=%s reason=%s" % (event.get("state"), event.get("reason")))
    if event.get("instance_is_new"):
        # ⚠ 전문을 남기지 않는다 — 이 값은 노드락 앵커다. 같은 배포인지 대조할 수 있으면
        #   충분하므로 앞 8자만 남긴다(2026-08-02: 그전에는 전문이 splunkd.log 에 찍혔다).
        _gid = str(event.get("manager_guid") or "")
        _log("INFO", "license seen on a new deployment id: %s" % (_gid[:8] + "…" if len(_gid) > 8 else _gid))

    payload = json.dumps(event, ensure_ascii=False, default=str)
    _emit([(name or "license_monitor", payload) for name in (stanzas or ["license_monitor"])])
    return 0


def main(argv):
    if len(argv) > 1:
        if argv[1] == "--scheme":
            sys.stdout.write(SCHEME)
            return 0
        if argv[1] == "--validate-arguments":
            return 0  # use_external_validation=false
    return run(sys.stdin.read())


if __name__ == "__main__":
    sys.exit(main(sys.argv))
