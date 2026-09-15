#!/usr/bin/env python
# bifrost_logs.py
# Splunk scripted input for TA-llmgateway
# Supports both SQLite (default) and PostgreSQL log stores
# No external pip installs required:
#   - SQLite:     uses Splunk bundled sqlite3
#   - PostgreSQL: uses bundled psycopg2-binary, platform-specific build under
#                 bin/windows_x86_64/lib/ or bin/linux_x86_64/lib/
#
# Logging: writes to $SPLUNK_HOME/var/log/splunk/ta_llmgateway.log via the
# logging module (NOT stderr) per Splunkbase AppInspect requirements.

from __future__ import print_function
import os
import sys
import json
import sqlite3
import platform
import datetime
import logging
import logging.handlers

# Add bundled lib path for psycopg2 (platform-specific compiled binary)
APP_HOME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PLATFORM_DIR = "windows_x86_64" if platform.system() == "Windows" else "linux_x86_64"
LIB_PATH = os.path.join(APP_HOME, "bin", _PLATFORM_DIR, "lib")
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)

CHECKPOINT_FILE = os.path.join(APP_HOME, "local", "bifrost_checkpoint.txt")
SETTINGS_FILE   = os.path.join(APP_HOME, "local", "ta_llmgateway_settings.conf")

# ---------------------------------------------------------------------------
# Logging setup - writes to SPLUNK_HOME/var/log/splunk/ta_llmgateway.log
# ---------------------------------------------------------------------------
def setup_logger():
    logger = logging.getLogger("ta_llmgateway")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    splunk_home = os.environ.get("SPLUNK_HOME", "")
    log_dir = os.path.join(splunk_home, "var", "log", "splunk")
    try:
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)
        log_file = os.path.join(log_dir, "ta_llmgateway.log")
        handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
    except Exception:
        # Fall back to a null handler if log dir is not writable;
        # never write operational messages to stderr.
        handler = logging.NullHandler()
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s pid=%(process)d %(message)s"
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger

LOG = setup_logger()

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
def read_settings():
    defaults = {
        "db_path":      "",
        "pg_host":      "",
        "pg_port":      "5432",
        "pg_database":  "bifrost",
        "pg_user":      "",
        "pg_password":  "",
        "index":        "llmgateway",
        "interval":     "30",
        "batch_size":   "500",
    }
    if not os.path.exists(SETTINGS_FILE):
        return defaults
    settings = dict(defaults)
    with open(SETTINGS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#") and not line.startswith("["):
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip()
                if k in settings:
                    settings[k] = v
    return settings

# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------
def read_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r") as f:
                return f.read().strip()
        except Exception:
            pass
    dt = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.0000000Z")

def write_checkpoint(ts):
    local_dir = os.path.join(APP_HOME, "local")
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    with open(CHECKPOINT_FILE, "w") as f:
        f.write(ts)

# ---------------------------------------------------------------------------
# Record flattening
# ---------------------------------------------------------------------------
def flatten_record(record):
    for field in ("token_usage", "input_history", "output_history", "tool_calls", "selected_key", "metadata"):
        raw = record.get(field)
        if raw and isinstance(raw, str):
            try:
                record[field] = json.loads(raw)
            except Exception:
                pass

    tu = record.pop("token_usage", None)
    if isinstance(tu, dict):
        record["prompt_tokens"]     = tu.get("prompt_tokens", 0)
        record["completion_tokens"] = tu.get("completion_tokens", 0)
        record["total_tokens"]      = tu.get("total_tokens", 0)
    else:
        record["prompt_tokens"]     = 0
        record["completion_tokens"] = 0
        record["total_tokens"]      = 0

    input_history = record.pop("input_history", None) or []
    system_prompt = ""
    input_prompt  = ""
    if isinstance(input_history, list):
        for msg in input_history:
            if isinstance(msg, dict):
                if msg.get("role") == "system" and not system_prompt:
                    system_prompt = msg.get("content", "")
                if msg.get("role") == "user" and not input_prompt:
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
                        input_prompt = " ".join(parts)
                    else:
                        input_prompt = str(content)
    record["input_prompt"]  = input_prompt
    record["system_prompt"] = system_prompt

    output_history = record.pop("output_history", None) or []
    output_text = ""
    tool_calls  = None
    if isinstance(output_history, list):
        for msg in output_history:
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                if msg.get("content") and not output_text:
                    output_text = str(msg["content"])
                if msg.get("tool_calls") and tool_calls is None:
                    tool_calls = msg["tool_calls"]

    # Newer Bifrost schema: single output_message object (JSON string or dict)
    if not output_text:
        om = record.get("output_message")
        if om:
            if isinstance(om, str):
                try:
                    om = json.loads(om)
                except Exception:
                    om = None
            if isinstance(om, dict):
                if om.get("content"):
                    output_text = str(om["content"])
                if om.get("tool_calls") and tool_calls is None:
                    tool_calls = om["tool_calls"]

    record["output_text"] = output_text
    record["tool_calls"]  = json.dumps(tool_calls) if tool_calls else None

    sk = record.pop("selected_key", None)
    if isinstance(sk, dict):
        record["selected_key_id"]   = sk.get("id", "")
        record["selected_key_name"] = sk.get("name", "")

    record["gateway"] = "bifrost"

    for f in ("raw_request", "raw_response"):
        record.pop(f, None)

    return record

# ---------------------------------------------------------------------------
# SQLite backend
# ---------------------------------------------------------------------------
def fetch_sqlite(db_path, last_seen, batch_size):
    if not os.path.exists(db_path):
        LOG.error("logs.db not found at: %s", db_path)
        return []
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()
    cur.execute("PRAGMA table_info(logs)")
    columns = [row[1] for row in cur.fetchall()]
    cur.execute(
        "SELECT * FROM logs WHERE created_at > ? ORDER BY created_at ASC LIMIT ?",
        (last_seen, batch_size)
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]

# ---------------------------------------------------------------------------
# PostgreSQL backend
# ---------------------------------------------------------------------------
def fetch_postgres(settings, last_seen, batch_size):
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError as e:
        LOG.error("psycopg2 not available: %s", str(e))
        return []

    conn = psycopg2.connect(
        host=settings["pg_host"],
        port=int(settings["pg_port"]),
        dbname=settings["pg_database"],
        user=settings["pg_user"],
        password=settings["pg_password"],
        connect_timeout=10
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM logs WHERE created_at > %s ORDER BY created_at ASC LIMIT %s",
        (last_seen, batch_size)
    )
    rows = [dict(row) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    settings   = read_settings()
    batch_size = int(settings.get("batch_size", 500))
    last_seen  = read_checkpoint()
    newest_ts  = last_seen

    use_postgres = bool(settings.get("pg_host", "").strip())

    if use_postgres:
        if not settings.get("pg_user"):
            LOG.error("pg_host set but pg_user is missing. Check ta_llmgateway_settings.conf")
            return
        LOG.info("using PostgreSQL backend (%s:%s/%s)",
                 settings["pg_host"], settings["pg_port"], settings["pg_database"])
        try:
            rows = fetch_postgres(settings, last_seen, batch_size)
        except Exception as e:
            LOG.error("PostgreSQL error: %s", str(e))
            return
    else:
        db_path = settings.get("db_path", "").strip()
        if not db_path:
            LOG.error("No db_path or pg_host configured. Set via TA LLM Gateway setup page.")
            return
        LOG.info("using SQLite backend (%s)", db_path)
        try:
            rows = fetch_sqlite(db_path, last_seen, batch_size)
        except Exception as e:
            LOG.error("SQLite error: %s", str(e))
            return

    count = 0
    for row in rows:
        try:
            record = flatten_record(row)
            ts = str(record.get("timestamp") or record.get("created_at", ""))
            if ts > newest_ts:
                newest_ts = ts
            # Events go to STDOUT for Splunk ingestion
            print(json.dumps(record, default=str))
            count += 1
        except Exception as e:
            LOG.error("record error: %s", str(e))
            continue

    if count:
        LOG.info("emitted %d event(s)", count)

    if newest_ts != last_seen:
        write_checkpoint(newest_ts)

if __name__ == "__main__":
    main()
