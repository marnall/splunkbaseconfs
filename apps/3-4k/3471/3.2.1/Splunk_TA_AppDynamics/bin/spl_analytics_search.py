import sys
import os
import time
import traceback
import json
import re

# Add 'lib' directory (relative to this script) to the module path before local imports
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(APP_DIR, "lib")
sys.path.insert(0, LIB_DIR)

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from solnlib import splunkenv, log
from spl_base import BaseGeneratingCommand
from analytics_service import AnalyticsService

# Analytics API returns field labels like "Transaction Name" or "Duration (ms)" which break CSV header
_BAD_FIELD_CHARS = re.compile(r"[^\w]")


def _safe_key(name):
    """Splunk output protocol expects safe field names (no spaces, commas, parens)."""
    if not name or not isinstance(name, str):
        return "field"
    s = _BAD_FIELD_CHARS.sub("_", name).strip("_") or "field"
    return s if s else "field"


def _to_str(val):
    """All values as strings; strip newlines/cr that break CSV output."""
    if val is None:
        return ""
    if isinstance(val, (dict, list)):
        s = json.dumps(val, default=str) if val else ""
    else:
        s = str(val)
    return s.replace("\r", " ").replace("\n", " ").replace("\x00", "")[:65535]


def _ensure_time_and_raw(record, fallback_epoch_sec):
    """Normalize Analytics record so output matches what Splunk expects (safe keys, strings, _time, _raw)."""
    epoch_sec = fallback_epoch_sec
    for name in ("timestamp", "event_timestamp", "time", "start_time_ms", "startTime", "_time"):
        if name in record and record[name] is not None:
            try:
                val = record[name]
                if isinstance(val, (int, float)):
                    epoch_sec = val / 1000.0 if val > 1e12 else float(val)
                    break
                if isinstance(val, str) and val.replace(".", "", 1).replace("-", "", 1).isdigit():
                    n = float(val)
                    epoch_sec = n / 1000.0 if n > 1e12 else n
                    break
            except (TypeError, ValueError):
                pass
            break
    out = {}
    for k, v in record.items():
        out[_safe_key(k)] = _to_str(v)
    out["_time"] = epoch_sec  # always numeric for Splunk time column
    if "_raw" not in out or out.get("_raw") == "":
        out["_raw"] = json.dumps({k: v for k, v in record.items() if k != "_raw"}, default=str)[:65535]
    if "sourcetype" not in out or out.get("sourcetype") == "":
        out["sourcetype"] = "appdynamics_analytics"
    if "index" not in out or out.get("index") == "":
        out["index"] = "main"
    return out


@Configuration(streaming=True)
class AnalSearch(BaseGeneratingCommand):
    account = Option(doc='''
        **Syntax: account=<string>
        **Description:** Name of an Analytics Account stanza configured in the TA (Setup → AppDynamics → Analytics Accounts). This is not the Controller Account.''',
                     require=True)
    query = Option(doc='''
        **Syntax: query=<string>
        **Description:** the AppDynamics Analytics Query (ADQL) to execute.''',
                   require=True)
    pagesize = Option(doc='''
        **Syntax: pagesize=<integer>
        **Description:** Reserved (API limit caps total rows, so not used for paging).''',
                     require=False, default=None)
    limit = Option(doc='''
        **Syntax: limit=<integer>
        **Description:** Optional maximum total rows (API limit). Omit to return all results.''',
                   require=False, default=None)

    def generate(self):
        raw_account = self.get_arg("account") or ""
        self.account = raw_account.strip().strip('"').strip("'").strip() or raw_account
        raw_query = self.get_arg("query") or ""
        self.query = raw_query.strip().strip('"').strip("'").strip() or raw_query
        def _parse_int(val, default=None):
            if val is None or not str(val).strip():
                return default
            try:
                return max(1, int(val))
            except (TypeError, ValueError):
                return default
        self.pagesize = _parse_int(self.get_arg("pagesize"))
        self.limit = _parse_int(self.get_arg("limit"))
        search_earliest_time, search_latest_time = self.get_search_times()
        fallback_epoch_sec = search_earliest_time / 1000.0

        self.logger.info("Account '%s' search query: '%s' start: '%d' end: '%d' limit=%s", self.account, self.query, search_earliest_time, search_latest_time, self.limit)
        try:
            session_key = self.get_session_key()
            analytics = AnalyticsService(self.account, session_key)
            # Flush after every event so the UI can show results before Splunk's 50k buffer fills.
            # Splunk may still batch at the protocol level; if so, use maxrows= to cap and see results sooner.
            yielded = 0
            for batch in analytics.search_stream(self.query, start=search_earliest_time, end=search_latest_time, limit=self.limit, page_size=self.pagesize):
                for data in batch:
                    yield _ensure_time_and_raw(data, fallback_epoch_sec)
                    yielded += 1
                    self.flush()
        except Exception:
            self.logger.error(traceback.format_exc())
            raise


# ─── DISPATCH ENTRYPOINT ────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        dispatch(AnalSearch, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        raise
