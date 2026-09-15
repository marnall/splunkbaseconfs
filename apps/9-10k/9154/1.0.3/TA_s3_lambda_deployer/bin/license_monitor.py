"""
Modular input: license expiry monitor.

Runs on an interval INSIDE Splunk (reliable clock, independent of S3 traffic). Each run:
  1. reads the saved license key,
  2. verifies the license and computes the subscription state / days-to-expiry,
  3. writes a `license_status` event (sourcetype=s3_lambda_deployer:license) so admins
     can dashboard/alert on it with standard Splunk alerting.

The hard consequence the events surface: WHEN THE LICENSE EXPIRES, DATA COLLECTION
STOPS — the deployed Lambda refuses to send after the grace period (default 3 days).
The Deploy Pipeline tab shows the same countdown/state.
"""
import importlib.util
import json
import os
import sys

APP_NAME = "TA_s3_lambda_deployer"

# See the long note in deploy_lambda.py: never trust __file__/sys.path for our own
# sibling modules under Splunk. Resolve bin/ from SPLUNK_HOME too, and load siblings
# by explicit file path.


def _candidate_bins():
    cands = []
    try:
        cands.append(os.path.dirname(os.path.abspath(__file__)))
    except Exception:  # noqa: BLE001
        pass
    splunk_home = os.environ.get("SPLUNK_HOME")
    if splunk_home:
        cands.append(os.path.join(splunk_home, "etc", "apps", APP_NAME, "bin"))
    seen, out = set(), []
    for c in cands:
        if c and c not in seen and os.path.isdir(c):
            seen.add(c)
            out.append(c)
    return out


def _ensure_paths():
    for _b in _candidate_bins():
        for _p in (os.path.join(os.path.dirname(_b), "lib"), _b):
            if os.path.isdir(_p) and _p not in sys.path:
                sys.path.insert(0, _p)


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
    raise ImportError(f"cannot locate {name}.py (bins={_candidate_bins()})")


_ensure_paths()
try:
    import import_declare_test  # noqa: F401,E402
except ImportError:
    pass
_ensure_paths()

from splunklib import modularinput as smi  # noqa: E402
from solnlib import conf_manager  # noqa: E402

license_mod = _load_sibling("ta_license")
SETTINGS_CONF = "s3_lambda_deployer_settings"
SOURCETYPE = "s3_lambda_deployer:license"


def _read_config(session_key):
    cfm = conf_manager.ConfManager(
        session_key, APP_NAME,
        realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-{SETTINGS_CONF}",
    )
    conf = cfm.get_conf(SETTINGS_CONF)
    lic = conf.get("license") or {}
    return lic.get("license_key", "")


class LicenseMonitor(smi.Script):
    def get_scheme(self):
        scheme = smi.Scheme("S3 to Splunk license monitor")
        scheme.description = (
            "Writes hourly license_status events. Data collection STOPS when the "
            "license expires (after the grace period)."
        )
        scheme.use_external_validation = False
        scheme.use_single_instance = True
        scheme.add_argument(
            smi.Argument("name", title="Name", data_type=smi.Argument.data_type_string,
                         required_on_create=True)
        )
        return scheme

    def stream_events(self, inputs, ew):
        import datetime
        session_key = self._input_definition.metadata["session_key"]
        today = datetime.date.today()

        try:
            license_key = _read_config(session_key)
        except Exception as e:  # noqa: BLE001
            ew.log("ERROR", f"license_monitor: could not read config: {e}")
            return

        status = license_mod.verify_license(license_key)
        state, dr = license_mod.subscription_state(status, today)

        for _name in inputs.inputs:
            evt = {
                "state": state,
                "days_remaining": dr,
                "valid": status.get("valid"),
                "customer": status.get("customer"),
                "expiry": status.get("expiry"),
                "grace_days": status.get("grace_days"),
                "aws_account": status.get("aws_account"),
                "reason": status.get("reason"),
                # spelled out so a bare event search already carries the consequence
                "consequence": (
                    "DATA COLLECTION HAS STOPPED — renew the license and re-deploy"
                    if state == "stopped" else
                    "EXPIRED — ingestion continues only during the grace period, then STOPS"
                    if state == "grace" else
                    "data collection stops at expiry + grace period"
                ),
            }
            ew.write_event(smi.Event(
                data=json.dumps(evt), sourcetype=SOURCETYPE, source="license_monitor",
            ))


if __name__ == "__main__":
    sys.exit(LicenseMonitor().run(sys.argv))
