#!/usr/bin/env python3
"""
CIM Assessment Report - Generate & Email
Machine Data Insights Inc.

Copyright 2025-2026 Machine Data Insights Inc.
Licensed under the Apache License, Version 2.0
See LICENSE file for details.

Splunk alert action script that:
1. Reads SMTP settings from Splunk's configured mail settings
2. Exports report CSVs via Splunk REST API (localhost)
3. Generates the Word document (python-docx)
4. Emails the report to configured recipients

Configuration (in macros.conf or via Splunk UI):
  cim_validator_environment  - Environment name (e.g., "Production")
  cim_report_recipients      - Comma-separated email addresses
  cim_report_sender          - From address (defaults to Splunk's configured sender)

SMTP password resolution order:
  1. --smtp-password CLI argument
  2. Splunk credential store (realm=CIM_Assessment_Toolkit, username=smtp_password)
  3. Splunk's alert_actions.conf auth_password (usually encrypted/unusable)

Usage:
  Triggered automatically as a scheduled saved search action, or manually:
    python3 email_report.py [--env "Production"] [--recipients "a@co.com,b@co.com"]
"""

import os
import sys
import json
import csv
import smtplib
import ssl
import socket
import argparse
import urllib.request
import urllib.parse
import urllib.error
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone

# ── Configuration ──────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
REPORT_GEN = os.path.join(SCRIPT_DIR, "generate_report.py")

# Writable base for CSV exports and generated .docx files. Splunk Cloud
# mounts the app's bin/ read-only, so when SPLUNK_HOME is set (the alert
# action context), write under var/run/splunk/<app>/. For manual CLI use
# without SPLUNK_HOME (developer environments), fall back to bin/.
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
if SPLUNK_HOME:
    WRITABLE_BASE = os.path.join(SPLUNK_HOME, "var", "run", "splunk", "CIM_Assessment_Toolkit")
else:
    WRITABLE_BASE = SCRIPT_DIR

# Splunk REST API - always localhost since this runs on the Splunk server
SPLUNK_URI = "https://127.0.0.1:8089"

# ── SSL Context (trust localhost self-signed cert) ─────────────────────
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def splunk_rest_get(path, token):
    """Make an authenticated GET request to Splunk REST API."""
    url = f"{SPLUNK_URI}{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Splunk {token}")
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"  REST GET {path}: {e.code} {e.reason}", file=sys.stderr)
        return None


def splunk_rest_post(path, data, token):
    """Make an authenticated POST request to Splunk REST API."""
    url = f"{SPLUNK_URI}{path}"
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    req.add_header("Authorization", f"Splunk {token}")
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=600)
        return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"  REST POST {path}: {e.code} {e.reason}", file=sys.stderr)
        return None
    except (socket.timeout, urllib.error.URLError) as e:
        raise Exception(f"Request timed out after 600s: {path}")


def run_async_search(token, search, earliest="-24h@h", latest="now", timeout=600):
    """Run a search via async job create/poll/fetch — works for all search types."""
    import time
    # Create job
    data = {
        "search": search,
        "earliest_time": earliest,
        "latest_time": latest,
        "output_mode": "json",
    }
    result = splunk_rest_post("/services/search/jobs", data, token)
    if not result:
        return None
    try:
        sid = json.loads(result).get("sid")
    except (json.JSONDecodeError, KeyError):
        # Try XML parsing as fallback
        import re
        m = re.search(r'<sid>([^<]+)</sid>', result)
        sid = m.group(1) if m else None
    if not sid:
        return None

    # Poll for completion
    start_time = time.time()
    while time.time() - start_time < timeout:
        status_raw = splunk_rest_get(f"/services/search/jobs/{sid}?output_mode=json", token)
        if status_raw:
            try:
                status = json.loads(status_raw)
                entry = status.get("entry", [{}])[0].get("content", {})
                if entry.get("isDone"):
                    break
                if entry.get("isFailed"):
                    print(f"  Async search failed: {entry.get('messages', '')}", file=sys.stderr)
                    return None
            except (json.JSONDecodeError, IndexError):
                pass
        time.sleep(2)
    else:
        print(f"  Async search timed out after {timeout}s", file=sys.stderr)
        return None

    # Fetch results as CSV
    fetch_url = f"{SPLUNK_URI}/services/search/jobs/{sid}/results?output_mode=csv&count=0"
    req = urllib.request.Request(fetch_url)
    req.add_header("Authorization", f"Splunk {token}")
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=60)
        return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  Failed to fetch results for {sid}: {e}", file=sys.stderr)
        return None


def get_session_token(username, password):
    """Authenticate and get a session token."""
    url = f"{SPLUNK_URI}/services/auth/login"
    data = urllib.parse.urlencode({
        "username": username,
        "password": password,
        "output_mode": "json"
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        result = json.loads(resp.read().decode("utf-8"))
        return result.get("sessionKey")
    except Exception as e:
        print(f"  Authentication failed: {e}", file=sys.stderr)
        return None


def get_splunk_mail_settings(token):
    """Read Splunk's configured email/SMTP settings."""
    raw = splunk_rest_get(
        "/services/configs/conf-alert_actions/email?output_mode=json", token
    )
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        content = data["entry"][0]["content"]
        settings = {
            "mailserver": content.get("mailserver", "localhost:25"),
            "use_ssl": content.get("use_ssl", "0"),
            "use_tls": content.get("use_tls", "0"),
            "auth_username": content.get("auth_username", ""),
            "auth_password": content.get("clear_password", content.get("auth_password", "")),
            "from": content.get("from", "splunk@localhost"),
        }

        # If password is encrypted ($7$...), try the admin endpoint for clear_password
        if settings["auth_password"].startswith("$7$") or settings["auth_password"].startswith("$1$"):
            admin_raw = splunk_rest_get(
                "/servicesNS/nobody/system/admin/alert_actions/email?output_mode=json", token
            )
            if admin_raw:
                try:
                    admin_data = json.loads(admin_raw)
                    admin_content = admin_data["entry"][0]["content"]
                    clear = admin_content.get("clear_password", "")
                    if clear and not clear.startswith("$"):
                        settings["auth_password"] = clear
                except (KeyError, IndexError, json.JSONDecodeError):
                    pass

        return settings
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"  Warning: Could not parse mail settings: {e}", file=sys.stderr)
        return {}


def get_stored_credential(token, realm="CIM_Assessment_Toolkit", username="smtp_password"):
    """Read a credential from Splunk's credential store (/services/storage/passwords).

    This is the preferred method for storing the SMTP password securely.
    Splunk encrypts the value at rest and returns clear_password via REST.

    To store: Settings > Users and Authentication > Credentials > New Credential
      Realm: CIM_Assessment_Toolkit
      Username: smtp_password
      Password: <your SMTP password>
    """
    raw = splunk_rest_get(
        f"/servicesNS/nobody/CIM_Assessment_Toolkit/storage/passwords"
        f"?output_mode=json&search={urllib.parse.quote(f'realm={realm} username={username}')}",
        token
    )
    if not raw:
        return None
    try:
        data = json.loads(raw)
        for entry in data.get("entry", []):
            content = entry.get("content", {})
            if content.get("realm") == realm and content.get("username") == username:
                clear = content.get("clear_password", "")
                if clear and not clear.startswith("$"):
                    return clear
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def get_macro_value(token, macro_name):
    """Read a macro definition from Splunk."""
    raw = splunk_rest_get(
        f"/servicesNS/nobody/CIM_Assessment_Toolkit/configs/conf-macros/{macro_name}?output_mode=json",
        token
    )
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data["entry"][0]["content"].get("definition", "").strip('"').strip("'")
    except (KeyError, IndexError, json.JSONDecodeError):
        return None


def export_search_csv(token, search, filepath, earliest="-24h@h", latest="now"):
    """Export a Splunk search to CSV via the export endpoint."""
    filename = os.path.basename(filepath)
    data = {
        "search": search,
        "earliest_time": earliest,
        "latest_time": latest,
        "output_mode": "csv",
    }
    try:
        result = splunk_rest_post("/services/search/jobs/export", data, token)
    except Exception as e:
        # Write empty file and report the error
        open(filepath, "w").close()
        print(f"  {filename}: TIMEOUT/ERROR - {e}")
        return False
    if result:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(result)
        size = os.path.getsize(filepath)
        print(f"  {filename}: {size} bytes")
        return size > 0
    else:
        # Write empty file
        open(filepath, "w").close()
        print(f"  {filename}: FAILED (empty response)")
        return False


def export_acceleration_csv(token, filepath):
    """Export acceleration health by querying each CIM model individually."""
    cim_models = [
        "Alerts", "Authentication", "Certificates", "Change", "Compute_Inventory",
        "DLP", "Databases", "Email", "Endpoint", "Event_Signatures",
        "Interprocess_Messaging", "Intrusion_Detection", "JVM", "Malware",
        "Network_Resolution", "Network_Sessions", "Network_Traffic",
        "Performance", "Splunk_Audit", "Ticket_Management",
        "Updates", "Vulnerabilities", "Web",
    ]

    rows = []
    for model in cim_models:
        encoded = urllib.parse.quote(f"tstats:DM_Splunk_SA_CIM_{model}", safe="")
        raw = splunk_rest_get(
            f"/services/admin/summarization/{encoded}?output_mode=json", token
        )
        if not raw:
            continue
        try:
            data = json.loads(raw)
            if not data.get("entry"):
                continue
            c = data["entry"][0]["content"]

            complete_pct = round(float(c.get("summary.complete", 0)) * 100, 1)
            is_building = int(c.get("summary.is_inprogress", 0))
            last_error = str(c.get("summary.last_error", "") or "")
            if last_error in ("None", "none"):
                last_error = ""

            if last_error:
                status = "Error"
            elif complete_pct >= 99.9:
                status = "Complete"
            elif is_building:
                status = "Building"
            else:
                status = "Incomplete"

            e_time = c.get("summary.earliest_time")
            l_time = c.get("summary.latest_time")
            earliest = "N/A"
            latest = "N/A"
            if e_time and float(e_time) > 0:
                earliest = datetime.fromtimestamp(float(e_time)).strftime("%Y-%m-%d %H:%M")
            if l_time and float(l_time) > 0:
                latest = datetime.fromtimestamp(float(l_time)).strftime("%Y-%m-%d %H:%M")

            ret = c.get("summary.time_range") or c.get("summary.retention")
            ret_days = "N/A"
            if ret and float(ret) > 0:
                ret_days = str(round(float(ret) / 86400, 1))

            searches = c.get("summary.access_count", 0)

            rows.append({
                "Data Model": model,
                "app": "Splunk_SA_CIM",
                "status": status,
                "Complete %": str(complete_pct),
                "Earliest": earliest,
                "Latest": latest,
                "Retention (days)": ret_days,
                "Searches": str(searches),
                "Last Error": last_error,
            })
        except (KeyError, ValueError, json.JSONDecodeError):
            continue

    # Write CSV
    headers = ["Data Model", "app", "status", "Complete %", "Earliest", "Latest",
               "Retention (days)", "Searches", "Last Error"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    size = os.path.getsize(filepath)
    print(f"  acceleration.csv: {size} bytes ({len(rows)} models)")
    return len(rows) > 0


def send_email(mail_settings, recipients, sender, subject, body, attachment_path, token=None):
    """Send email with attachment using Splunk's SMTP settings."""
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    # Attach the report
    with open(attachment_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={os.path.basename(attachment_path)}"
        )
        msg.attach(part)

    # Parse mail server
    server_str = mail_settings.get("mailserver", "localhost:25")
    if ":" in server_str:
        host, port = server_str.rsplit(":", 1)
        port = int(port)
    else:
        host = server_str
        port = 25

    use_ssl = str(mail_settings.get("use_ssl", "0")) in ("1", "true", "True")
    use_tls = str(mail_settings.get("use_tls", "0")) in ("1", "true", "True")
    auth_user = mail_settings.get("auth_username", "")
    auth_pass = mail_settings.get("auth_password", "")

    # Splunk's REST API always returns encrypted passwords from alert_actions.conf.
    # The credential store or --smtp-password flag provides the clear-text password.
    if auth_pass.startswith("$7$") or auth_pass.startswith("$1$"):
        auth_pass = ""
    if not auth_pass:
        print(f"  SMTP password: not available (store in Splunk credential store via setup page, or use --smtp-password)")

    try:
        print(f"  SMTP: {host}:{port} (ssl={use_ssl}, tls={use_tls}, auth={bool(auth_user)})")
        if use_ssl:
            smtp = smtplib.SMTP_SSL(host, port, context=ctx, timeout=30)
        else:
            smtp = smtplib.SMTP(host, port, timeout=30)
            smtp.ehlo()
            if use_tls or port == 587:
                smtp.starttls(context=ctx)
                smtp.ehlo()

        if auth_user and auth_pass:
            smtp.login(auth_user, auth_pass)

        smtp.sendmail(sender, recipients, msg.as_string())
        smtp.quit()
        print(f"  Email sent to: {', '.join(recipients)}")
        return True
    except Exception as e:
        print(f"  Email FAILED: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="CIM Assessment Report Generator & Emailer")
    parser.add_argument("--env", default=None, help="Environment name")
    parser.add_argument("--recipients", default=None, help="Comma-separated email addresses")
    parser.add_argument("--sender", default=None, help="From email address")
    parser.add_argument("--username", default=None, help="Splunk username")
    parser.add_argument("--password", default=None, help="Splunk password")
    parser.add_argument("--token", default=None, help="Splunk session token (alternative to user/pass)")
    parser.add_argument("--output-dir", default=None, help="Output directory for report")
    parser.add_argument("--scope", default=None, help="Report scope: all, security, operational, or custom category")
    parser.add_argument("--smtp-password", default=None, help="SMTP password (if Splunk REST doesn't return clear_password)")
    parser.add_argument("--no-email", action="store_true", help="Generate report only, don't email")
    args, _unknown = parser.parse_known_args()

    print("=" * 60)
    print("CIM Assessment Report - Generate & Email")
    print("=" * 60)

    # ── Authentication ─────────────────────────────────────────────────
    token = args.token

    if not token:
        # When triggered by Splunk alert action, session key may be in env
        token = os.environ.get("SPLUNK_SESSION_KEY")

    if not token:
        # For Splunk custom alert actions, session key comes via stdin as JSON
        if not sys.stdin.isatty():
            try:
                stdin_data = sys.stdin.read()
                if stdin_data.strip().startswith("{"):
                    payload = json.loads(stdin_data)
                    token = payload.get("session_key")
                elif stdin_data.strip():
                    # Raw session key on stdin
                    token = stdin_data.strip()
            except (json.JSONDecodeError, IOError):
                pass

    if not token:
        # Manual mode - authenticate with username/password
        username = args.username
        password = args.password
        if not username:
            if sys.stdin.isatty():
                username = input("Splunk username: ")
            else:
                print("ERROR: No session token and no interactive terminal for login", file=sys.stderr)
                sys.exit(1)
        if not password:
            if sys.stdin.isatty():
                import getpass
                password = getpass.getpass("Splunk password: ")
            else:
                print("ERROR: No session token and no interactive terminal for password entry", file=sys.stderr)
                sys.exit(1)
        print("Authenticating...")
        token = get_session_token(username, password)
        if not token:
            print("ERROR: Authentication failed", file=sys.stderr)
            sys.exit(1)

    # ── Read Configuration ─────────────────────────────────────────────
    print("Reading configuration...")

    env_name = args.env or get_macro_value(token, "cim_validator_environment") or "Production"
    recipients_str = args.recipients or get_macro_value(token, "cim_report_recipients") or ""
    sender = args.sender

    mail_settings = get_splunk_mail_settings(token)
    if not sender:
        sender = get_macro_value(token, "cim_report_sender") or mail_settings.get("from", "splunk@localhost")

    # SMTP password priority: CLI arg > credential store > Splunk config
    if args.smtp_password:
        mail_settings["auth_password"] = args.smtp_password
        print("  SMTP password: from --smtp-password argument")
    else:
        stored_pass = get_stored_credential(token)
        if stored_pass:
            mail_settings["auth_password"] = stored_pass
            print("  SMTP password: from Splunk credential store")

    # Strip any surrounding quotes before splitting so the macro accepts both
    # "a@x.com,b@y.com" and "a@x.com","b@y.com" formats.
    recipients = [r.strip() for r in recipients_str.replace('"', '').split(",") if r.strip()]

    print(f"  Environment: {env_name}")
    print(f"  Recipients: {', '.join(recipients) if recipients else '(none - report only)'}")
    print(f"  SMTP: {mail_settings.get('mailserver', 'not configured')}")

    # Read trend days for comparison
    trend_days_str = get_macro_value(token, "cim_report_trend_days") or "7"
    try:
        trend_days = int(trend_days_str)
    except ValueError:
        trend_days = 7
    print(f"  Trend comparison: {trend_days} days")

    # Read report scope (security, operational, all, or custom category)
    scope = args.scope or get_macro_value(token, "cim_report_scope") or "all"
    scope = scope.strip().strip('"').strip("'").lower()
    print(f"  Report scope: {scope}")

    # Build SPL filter fragment for category scoping
    if scope == "all":
        scope_filter = ""
        scope_label = ""
    else:
        scope_filter = f' | lookup cim_model_categories model as modelName | where like(category, "%{scope}%")'
        scope_label = f" ({scope.title()})"

    # ── Export Data ────────────────────────────────────────────────────
    data_dir = os.path.join(WRITABLE_BASE, "report_data")
    os.makedirs(data_dir, exist_ok=True)
    # Clear previous export data
    for f in os.listdir(data_dir):
        if f.endswith(".csv"):
            os.remove(os.path.join(data_dir, f))
    print(f"\nExporting report data...")

    # KPI Summary
    export_search_csv(token, f'''search `cim_validator_base_search`{scope_filter} | eval percent_coverage = if(percent_coverage > 100, 100, percent_coverage) | bin _time span=1d | eval is_rec = if(field_class IN ("required", "recommended"), 1, 0) | eval is_rec_mapped = if(is_rec=1 AND field_count > 0, 1, 0) | eval has_pv = if(isnotnull(value_compliance_pct), 1, 0) | eval pv_compliant = if(has_pv=1 AND value_compliance_pct >= 80, 1, 0) | eventstats sum(is_rec) as total_rec_fields sum(is_rec_mapped) as mapped_rec_fields avg(eval(if(is_rec=1, percent_coverage, null()))) as percent_data_coverage sum(has_pv) as total_pv_fields sum(pv_compliant) as compliant_pv_fields by modelName dataset index sourcetype | eval rec_field_coverage_pct = round(mapped_rec_fields / total_rec_fields * 100, 2) | eval percent_data_coverage = round(percent_data_coverage, 2) | eval value_quality_pct = if(total_pv_fields > 0, round(compliant_pv_fields / total_pv_fields * 100, 2), null()) | eval overall_quality_pct = round((rec_field_coverage_pct + percent_data_coverage) / 2, 2) | dedup modelName dataset index sourcetype | stats avg(rec_field_coverage_pct) as mapping_quality avg(percent_data_coverage) as data_quality avg(eval(if(isnotnull(value_quality_pct), value_quality_pct, null()))) as value_compliance avg(overall_quality_pct) as overall_quality | eval mapping_quality=round(mapping_quality,1) | eval data_quality=round(data_quality,1) | eval value_compliance=round(value_compliance,1) | eval overall_quality=round(overall_quality,1)''',
        os.path.join(data_dir, "kpi.csv"))

    # CIM Coverage (live tstats — same query as dashboard KPI, scope-aware)
    if scope == "all":
        cim_scope_filter_join = ""
        cim_scope_filter_denom = ""
    else:
        cim_scope_filter_join = f' | lookup cim_model_categories model as modelName | where like(category, "%{scope}%")'
        cim_scope_filter_denom = (
            f' | eval scope = if(isnotnull(scope), scope, "unknown")'
            f' | where like(scope, "%{scope}%")'
        )
    cim_coverage_spl = (
        f'| tstats count WHERE index=* NOT index=_* NOT index=`cim_validator_index` BY sourcetype'
        f' | join type=left sourcetype'
        f' [| search `cim_validator_base_search`{cim_scope_filter_join}'
        f' | stats dc(modelName) as model_count by sourcetype]'
        f' | eval is_mapped = if(isnotnull(model_count) AND model_count > 0, 1, 0)'
        f' | lookup cim_sourcetype_inventory sourcetype OUTPUT scope'
        f' | join type=left sourcetype'
        f' [| inputlookup cim_sourcetype_exclusions'
        f' | eval exclude = if(match(lower(trim(exclude)), "^(n|no|f|false|0)$"), "N", "Y")'
        f' | fields sourcetype exclude]'
        f' | eval exclude = if(isnull(exclude), "N", exclude)'
        f' | where NOT (exclude="Y")'
        f'{cim_scope_filter_denom}'
        f' | stats sum(is_mapped) as mapped count as total'
        f' | eval cim_coverage = round(mapped / total * 100, 1)'
    )
    # tstats + join requires async job
    cim_cov_result = run_async_search(token, cim_coverage_spl)
    cim_cov_path = os.path.join(data_dir, "cim_coverage.csv")
    if cim_cov_result and len(cim_cov_result.strip()) > 10:
        with open(cim_cov_path, "w", encoding="utf-8") as f:
            f.write(cim_cov_result)
        print(f"  cim_coverage.csv: {os.path.getsize(cim_cov_path)} bytes")
    else:
        with open(cim_cov_path, "w", encoding="utf-8") as f:
            f.write("mapped,total,cim_coverage\n")
        print("  cim_coverage.csv: (empty — tstats returned no data)")

    # Compliance Detail
    export_search_csv(token, f'''search `cim_validator_base_search`{scope_filter} | eval percent_coverage = if(percent_coverage > 100, 100, percent_coverage) | bin _time span=1d | eval is_rec = if(field_class IN ("required", "recommended"), 1, 0) | eval is_rec_mapped = if(is_rec=1 AND field_count > 0, 1, 0) | eventstats sum(is_rec) as total_rec_fields sum(is_rec_mapped) as mapped_rec_fields avg(eval(if(is_rec=1, percent_coverage, null()))) as percent_data_coverage by modelName dataset index sourcetype | eval rec_field_coverage_pct = round(mapped_rec_fields / total_rec_fields * 100, 2) | eval percent_data_coverage = round(percent_data_coverage, 2) | eval overall_quality_pct = round((rec_field_coverage_pct + percent_data_coverage) / 2, 2) | dedup modelName dataset index sourcetype | stats avg(rec_field_coverage_pct) as "Mapping %" avg(percent_data_coverage) as "Data Quality %" avg(overall_quality_pct) as "Overall %" dc(index) as indexes dc(sourcetype) as sourcetypes by modelName dataset | eval "Mapping %" = round('Mapping %', 1) | eval "Data Quality %" = round('Data Quality %', 1) | eval "Overall %" = round('Overall %', 1) | rename modelName as "Data Model" dataset as "Dataset" | sort "Data Model" Dataset''',
        os.path.join(data_dir, "compliance_detail.csv"))

    # Compliance Summary
    export_search_csv(token, f'''search `cim_validator_base_search`{scope_filter} | eval percent_coverage = if(percent_coverage > 100, 100, percent_coverage) | bin _time span=1d | eval is_rec = if(field_class IN ("required", "recommended"), 1, 0) | eval is_rec_mapped = if(is_rec=1 AND field_count > 0, 1, 0) | eval has_pv = if(isnotnull(value_compliance_pct), 1, 0) | eval pv_compliant = if(has_pv=1 AND value_compliance_pct >= 80, 1, 0) | eventstats sum(is_rec) as total_rec_fields sum(is_rec_mapped) as mapped_rec_fields avg(eval(if(is_rec=1, percent_coverage, null()))) as percent_data_coverage max(total_count) as event_count sum(has_pv) as total_pv_fields sum(pv_compliant) as compliant_pv_fields values(eval(if(is_rec=1 AND is_rec_mapped=0, field, null()))) as missing_rec_fields by modelName dataset index sourcetype | eval rec_field_coverage_pct = round(mapped_rec_fields / total_rec_fields * 100, 2) | eval percent_data_coverage = round(percent_data_coverage, 2) | eval value_quality_pct = if(total_pv_fields > 0, round(compliant_pv_fields / total_pv_fields * 100, 2), null()) | eval overall_quality_pct = round((rec_field_coverage_pct + percent_data_coverage) / 2, 2) | dedup modelName dataset index sourcetype | rename modelName as "Data Model" dataset as "Dataset" rec_field_coverage_pct as "Mapping %" percent_data_coverage as "Data Quality %" value_quality_pct as "Value Compliance" overall_quality_pct as "Overall %" event_count as "Events" missing_rec_fields as "Missing Fields" | table "Data Model" Dataset index sourcetype "Mapping %" "Data Quality %" "Value Compliance" "Overall %" Events "Missing Fields" | sort "Data Model" Dataset sourcetype''',
        os.path.join(data_dir, "compliance_summary.csv"))

    # Field Gaps — aggregate across indexes to one row per model/dataset/sourcetype/field
    export_search_csv(token, f'''search `cim_validator_base_search`{scope_filter} | eval percent_coverage = if(percent_coverage > 100, 100, percent_coverage) | search field_class IN ("required", "recommended") | stats max(total_count) as total_count sum(field_count) as field_count max(distinct_count) as distinct_count avg(percent_coverage) as percent_coverage latest(field_class) as field_class sum(compliant_count) as compliant_count avg(value_compliance_pct) as value_compliance_pct by modelName dataset sourcetype field | eval pv_rounded = round(value_compliance_pct, 1) | where field_count=0 OR (isnotnull(value_compliance_pct) AND pv_rounded < 100) | eval pv_display = if(isnotnull(value_compliance_pct), tostring(pv_rounded)."%", "---") | fields - pv_rounded | rename modelName as "Data Model" dataset as "Dataset" field as "Field" field_class as "Class" field_count as "Count" percent_coverage as "Coverage %" pv_display as "Value Compliance" | table "Data Model" Dataset sourcetype Field Class Count "Coverage %" "Value Compliance" | sort "Data Model" Dataset sourcetype -Class Field''',
        os.path.join(data_dir, "field_gaps.csv"))

    # Unmapped Sourcetypes — use async job with tstats (fast, works for all search types)
    unmapped_path = os.path.join(data_dir, "unmapped.csv")
    # Load sourcetype inventory (enrichment) and exclusions (two separate lookups)
    lookups_dir = os.path.join(SCRIPT_DIR, "..", "lookups")
    transforms_conf = os.path.join(SCRIPT_DIR, "..", "default", "transforms.conf")
    # local (user-modified) transforms.conf takes precedence, so a client that
    # redirects a lookup definition to a custom filename is honored here too.
    transforms_local = os.path.join(SCRIPT_DIR, "..", "local", "transforms.conf")

    def resolve_lookup_filename(stanza, default_name):
        """Read a lookup's filename from transforms.conf (local overrides default)
        so renamed/redirected lookups resolve to the right CSV on disk."""
        for tf_path in [transforms_local, transforms_conf]:
            if os.path.isfile(tf_path):
                in_stanza = False
                with open(tf_path, "r", encoding="utf-8") as tf:
                    for line in tf:
                        line = line.strip()
                        if line == "[" + stanza + "]":
                            in_stanza = True
                        elif line.startswith("[") and in_stanza:
                            break
                        elif in_stanza and line.startswith("filename"):
                            return line.split("=", 1)[1].strip()
                if in_stanza:
                    break
        return default_name

    # Inventory — enrichment only (vendor, relevance, scope, etc.)
    inventory_filename = resolve_lookup_filename(
        "cim_sourcetype_inventory", "cim_sourcetype_inventory.csv")
    inventory_file = os.path.join(lookups_dir, inventory_filename)
    print(f"  Inventory file: {inventory_filename}")
    inventory_lookup = {}  # sourcetype -> row dict for enrichment
    if os.path.isfile(inventory_file):
        with open(inventory_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                st = row.get("sourcetype", "").strip()
                if st:
                    inventory_lookup[st] = row
        print(f"  Loaded {len(inventory_lookup)} sourcetypes from inventory")
    else:
        print(f"  WARNING: Inventory file not found: {inventory_file}")

    # Exclusions — separate lookup. Read defensively: if the file is missing or
    # unreadable, nothing is excluded and the report still runs (matches the
    # dashboard's fault-tolerant subsearch behavior). The exclude column is
    # case-insensitive; blank (or a bare sourcetype with no exclude column) means
    # excluded, so a plain list of sourcetypes is sufficient to exclude them.
    excluded_sourcetypes = set()
    _EXCLUDE_FALSE = {"n", "no", "f", "false", "0"}
    exclusions_filename = resolve_lookup_filename(
        "cim_sourcetype_exclusions", "sourcetype_exclusions.csv")
    exclusions_file = os.path.join(lookups_dir, exclusions_filename)
    try:
        if os.path.isfile(exclusions_file):
            with open(exclusions_file, "r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    st = (row.get("sourcetype", "") or "").strip()
                    if not st:
                        continue
                    if (row.get("exclude", "") or "").strip().lower() not in _EXCLUDE_FALSE:
                        excluded_sourcetypes.add(st)
            print(f"  Exclusions file: {exclusions_filename} "
                  f"({len(excluded_sourcetypes)} excluded)")
        else:
            print(f"  Exclusions file not found ({exclusions_filename}); "
                  f"no sourcetypes excluded")
    except (OSError, csv.Error, ValueError) as e:
        excluded_sourcetypes = set()
        print(f"  WARNING: Could not read exclusions file "
              f"({exclusions_filename}); no sourcetypes excluded: {e}")

    # Inventory version sidecar (human-maintained changelog CSV). Surfaced as
    # an "as of" line in the report. Filename mirrors the lookup file:
    # <inventory>.version.csv  (columns: last_updated, updated_by, note,
    # base_catalog_last_updated). All columns are carried through generically.
    sidecar_file = os.path.join(lookups_dir, inventory_filename + ".version.csv")
    if os.path.isfile(sidecar_file):
        try:
            with open(sidecar_file, "r", encoding="utf-8-sig") as sf:
                sidecar_rows = list(csv.DictReader(sf))
            sidecar = ({k.strip(): (v or "").strip()
                        for k, v in sidecar_rows[0].items() if k}
                       if sidecar_rows else {})
            with open(os.path.join(data_dir, "inventory_version.json"), "w",
                      encoding="utf-8") as out:
                json.dump(sidecar, out)
            _bc = sidecar.get("base_catalog_last_updated", "")
            print(f"  Inventory sidecar: as of "
                  f"{sidecar.get('last_updated', 'unknown')}"
                  + (f" (base catalog {_bc})" if _bc else ""))
        except (ValueError, OSError, IndexError) as e:
            print(f"  WARNING: Could not read inventory sidecar: {e}")

    excluded_count = 0

    print("  Exporting unmapped/mapped via async tstats...")
    tstats_result = run_async_search(token,
        f'| tstats count WHERE index=* NOT index=_* NOT index=`cim_validator_index` BY sourcetype'
        f' | join type=left sourcetype'
        f' [| search `cim_validator_base_search`{scope_filter}'
        f' | stats dc(modelName) as model_count values(modelName) as mapped_models by sourcetype]'
        f' | eval is_mapped = if(isnotnull(model_count) AND model_count > 0, "Yes", "No")')

    if tstats_result and len(tstats_result.strip()) > 10:
        # Parse the full result, write unmapped and mapped separately
        import io
        reader = csv.DictReader(io.StringIO(tstats_result))
        all_rows = list(reader)
        all_unmapped = [r for r in all_rows if r.get("is_mapped") == "No"]
        unmapped_rows = [r for r in all_unmapped if r.get("sourcetype", "") not in excluded_sourcetypes]
        excluded_rows = [r for r in all_unmapped if r.get("sourcetype", "") in excluded_sourcetypes]
        mapped_rows = [r for r in all_rows if r.get("is_mapped") == "Yes"]

        if excluded_rows:
            print(f"  Excluded {len(excluded_rows)} sourcetypes from unmapped list")
        excluded_count = len(excluded_rows)

        # Apply scope filter from inventory: if scope is "security", only show
        # sourcetypes classified as having that scope in the inventory.
        # Sourcetypes NOT in the inventory are always included (unknown = needs review).
        if scope != "all":
            before_scope = len(unmapped_rows)
            def matches_scope(r):
                st = r.get("sourcetype", "")
                inv = inventory_lookup.get(st)
                if inv is None:
                    return True  # not in inventory = unknown, include for review
                st_scope = inv.get("scope", "unknown")
                if st_scope == "unknown":
                    return True  # unknown scope = include for review
                return scope in st_scope
            unmapped_rows = [r for r in unmapped_rows if matches_scope(r)]
            scope_filtered = before_scope - len(unmapped_rows)
            if scope_filtered:
                print(f"  Scope filter '{scope}': {len(unmapped_rows)} shown, {scope_filtered} out of scope")

            # Same scope filter applies to mapped rows so the report's Mapped
            # Sourcetypes section matches the CIM Coverage / Mapped scorecard
            # counts on the dashboard (which are scope-aware).
            mapped_before = len(mapped_rows)
            mapped_rows = [r for r in mapped_rows if matches_scope(r)]
            mapped_filtered = mapped_before - len(mapped_rows)
            if mapped_filtered:
                print(f"  Scope filter '{scope}' (mapped): {len(mapped_rows)} shown, {mapped_filtered} out of scope")

        # Sort by relevance (high > med > low > none) then vendor, sourcetype
        relevance_order = {"high": 0, "med": 1, "low": 2, "none": 3, "unknown": 4, "": 4}

        # Write unmapped — enriched with inventory data
        with open(unmapped_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["sourcetype", "Events", "Vendor", "Tech Category", "Relevance", "Scope"])
            for r in sorted(unmapped_rows,
                           key=lambda x: (relevance_order.get(
                               inventory_lookup.get(x.get("sourcetype",""), {}).get("security_relevance","unknown"), 4),
                               inventory_lookup.get(x.get("sourcetype",""), {}).get("vendor","").lower(),
                               x.get("sourcetype","").lower())):
                st = r.get("sourcetype", "")
                inv = inventory_lookup.get(st, {})
                w.writerow([
                    st,
                    r.get("count", "0"),
                    inv.get("vendor", ""),
                    inv.get("tech_category", ""),
                    inv.get("security_relevance", "unknown"),
                    inv.get("scope", "unknown"),
                ])
        print(f"  unmapped.csv: {os.path.getsize(unmapped_path)} bytes ({len(unmapped_rows)} active, {len(excluded_rows)} excluded)")

        # Write mapped — enriched with inventory data, matching unmapped structure
        mapped_path = os.path.join(data_dir, "mapped.csv")
        with open(mapped_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["sourcetype", "Vendor", "Relevance", "Scope", "Events", "Mapped To"])
            for r in sorted(mapped_rows,
                           key=lambda x: (relevance_order.get(
                               inventory_lookup.get(x.get("sourcetype",""), {}).get("security_relevance","unknown"), 4),
                               inventory_lookup.get(x.get("sourcetype",""), {}).get("vendor","").lower(),
                               x.get("sourcetype","").lower())):
                st = r.get("sourcetype", "")
                inv = inventory_lookup.get(st, {})
                models = r.get("mapped_models", "")
                w.writerow([st, inv.get("vendor", ""), inv.get("security_relevance", "unknown"),
                            inv.get("scope", "unknown"), r.get("count", "0"), models])
        print(f"  mapped.csv: {os.path.getsize(mapped_path)} bytes ({len(mapped_rows)} sourcetypes)")
    else:
        print("  unmapped/mapped: async tstats returned no data, falling back to summary index...")
        # Unmapped: can't derive from summary index — write empty
        with open(unmapped_path, "w") as f:
            f.write("sourcetype,Events,Vendor,Tech Category,Relevance,Scope\n")
        print("  unmapped.csv: (empty — unmapped data unavailable via REST)")

        # Mapped: derive from summary index
        mapped_path = os.path.join(data_dir, "mapped.csv")
        export_search_csv(token, f'''search `cim_validator_base_search`{scope_filter} | stats max(total_count) as "Events" values(modelName) as models by sourcetype | eval "Mapped To" = mvjoin(models, ", ") | fields sourcetype Events "Mapped To" | sort sourcetype''',
            mapped_path)

    # Remediation Priorities
    export_search_csv(token, f'''search `cim_validator_base_search`{scope_filter} | eval percent_coverage = if(percent_coverage > 100, 100, percent_coverage) | search field_class IN ("required", "recommended") | bin _time span=1d | eval is_mapped = if(field_count > 0, 1, 0) | stats sum(is_mapped) as mapped_rec_fields dc(field) as total_rec_fields avg(percent_coverage) as percent_data_coverage max(total_count) as event_count values(eval(if(is_mapped=0, field, null()))) as missing_rec_fields avg(eval(if(isnotnull(value_compliance_pct), value_compliance_pct, null()))) as avg_value_compliance by modelName dataset index sourcetype | eval rec_field_coverage_pct = round(mapped_rec_fields / total_rec_fields * 100, 2) | eval percent_data_coverage = round(percent_data_coverage, 2) | eval overall_quality_pct = round((rec_field_coverage_pct + percent_data_coverage) / 2, 2) | eval priority_score = round((100 - overall_quality_pct) * log(event_count + 1), 2) | eval missing_rec_count = mvcount(missing_rec_fields) | fillnull value=0 missing_rec_count | lookup splunk_data_model_objects_fields model as modelName dataset OUTPUT constraints | eval required_tags = mvdedup(constraints) | eval required_tags = mvindex(required_tags, 0) | rex field=required_tags "tag=(?<required_tags>.+)" | rename modelName as "Data Model" dataset as "Dataset" overall_quality_pct as "Overall %" rec_field_coverage_pct as "Mapping %" event_count as "Events" priority_score as "Priority" missing_rec_count as "Missing #" required_tags as "Required Tags" | where Priority > 0 | table "Data Model" Dataset sourcetype "Overall %" "Mapping %" Events Priority "Missing #" "Required Tags" | sort "Data Model" Dataset sourcetype''',
        os.path.join(data_dir, "remediation.csv"))

    # Compliance Trends (prior snapshot for comparison based on cim_report_trend_days macro)
    # Use a 3-day window centered on the target day to ensure we capture data
    # regardless of collection timing / timezone alignment
    trend_earliest = f"-{trend_days + 2}d@d"
    trend_latest = f"-{max(trend_days - 1, 1)}d@d"
    print(f"  Trends window: {trend_earliest} to {trend_latest}")
    export_search_csv(token, f'''search `cim_validator_base_search`{scope_filter} | eval percent_coverage = if(percent_coverage > 100, 100, percent_coverage) | bin _time span=1d | eval is_rec = if(field_class IN ("required", "recommended"), 1, 0) | eval is_rec_mapped = if(is_rec=1 AND field_count > 0, 1, 0) | eventstats sum(is_rec) as total_rec_fields sum(is_rec_mapped) as mapped_rec_fields avg(eval(if(is_rec=1, percent_coverage, null()))) as percent_data_coverage by modelName dataset index sourcetype | eval rec_field_coverage_pct = round(mapped_rec_fields / total_rec_fields * 100, 2) | eval percent_data_coverage = round(percent_data_coverage, 2) | eval overall_quality_pct = round((rec_field_coverage_pct + percent_data_coverage) / 2, 2) | dedup modelName dataset index sourcetype | stats latest(overall_quality_pct) as "Prior Overall %" by modelName dataset | eval "Prior Overall %" = round('Prior Overall %', 1) | rename modelName as "Data Model" dataset as "Dataset"''',
        os.path.join(data_dir, "trends.csv"),
        earliest=trend_earliest, latest=trend_latest)

    # Prior CIM Coverage (from summary index snapshots, filtered by scope)
    export_search_csv(token, f'''search index=`cim_validator_index` ReportType="cim_coverage" scope="{scope}" | stats latest(cim_coverage) as prior_cim_coverage latest(mapped) as prior_mapped latest(total) as prior_total''',
        os.path.join(data_dir, "cim_coverage_prior.csv"),
        earliest=trend_earliest, latest=trend_latest)

    # Acceleration Health (direct REST per-model)
    export_acceleration_csv(token, os.path.join(data_dir, "acceleration.csv"))

    # ── Generate Report ────────────────────────────────────────────────
    output_dir = args.output_dir or os.path.join(WRITABLE_BASE, "reports")
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    report_filename = f"CIM_Assessment_Report_{env_name}{'_' + scope.title() if scope != 'all' else ''}_{timestamp}.docx"
    report_path = os.path.join(output_dir, report_filename)

    print(f"\nGenerating report: {report_filename}")
    print(f"  CSV data retained in: {data_dir}")
    try:
        from generate_report import generate_report
        generate_report(
            env_name=env_name,
            data_dir=data_dir,
            output_path=report_path,
            trend_days=trend_days,
            scope=scope,
            excluded_count=excluded_count,
        )
    except Exception as e:
        print(f"  ERROR generating report: {e}", file=sys.stderr)
        sys.exit(1)

    # ── Email Report ───────────────────────────────────────────────────
    if not args.no_email and recipients:
        print(f"\nEmailing report...")
        subject = f"CIM Assessment Report{scope_label} - {env_name} - {datetime.now().strftime('%Y-%m-%d')}"
        body = (
            f"CIM Assessment Report for the {env_name} environment.\n\n"
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
            f"Report attached as: {report_filename}\n\n"
            f"This is an automated report from the CIM Assessment Toolkit.\n"
        )
        send_email(mail_settings, recipients, sender, subject, body, report_path, token=token)
    elif not recipients:
        print("\n  No recipients configured. Set the cim_report_recipients macro in Splunk:")
        print("  Settings > Advanced search > Search macros > cim_report_recipients")
    else:
        print(f"\n  Report saved: {report_path}")

    # Auto-cleanup: keep the last N reports, delete older ones
    keep_reports = 10
    try:
        report_files = sorted(
            [f for f in os.listdir(output_dir)
             if f.startswith("CIM_Assessment_Report_") and f.endswith(".docx")],
            key=lambda f: os.path.getmtime(os.path.join(output_dir, f)),
            reverse=True
        )
        if len(report_files) > keep_reports:
            for old_file in report_files[keep_reports:]:
                os.remove(os.path.join(output_dir, old_file))
            removed = len(report_files) - keep_reports
            print(f"  Cleanup: removed {removed} old report(s), keeping last {keep_reports}")
    except OSError:
        pass  # Non-critical — don't fail the run over cleanup

    print("\nDone.")


if __name__ == "__main__":
    main()
