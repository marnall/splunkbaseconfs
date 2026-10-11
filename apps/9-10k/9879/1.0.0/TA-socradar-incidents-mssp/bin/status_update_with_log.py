#!/usr/bin/env python

import sys
import os
import re
import time
import json
from datetime import datetime
from urllib.parse import quote as _urlquote
import logging


# --- SOCRadar product User-Agent -----------------------------------------------
# Without this the add-on goes out as a plain `python-requests/x.y.z`, which is
# indistinguishable from any ad-hoc script on the SOCRadar side. A product token
# makes support triage possible (which add-on, which version, which Splunk) and
# lets a proxy or WAF allow this add-on by name.
#
# `python-requests/<version>` is deliberately kept as the LAST token: the SOCRadar
# edge (Cloudflare) accepts that token today and rejects `Python-urllib` with 403
# (measured 2026-09-20 against platform.socradar.com and taxii2.socradar.com).
# Reordering these tokens is a WAF risk.
_SOCRADAR_UA_CACHE = None


def socradar_user_agent():
    """`SOCRadar-Splunk-TA-<app>/<version> (Splunk/<version>; python-requests/<version>)`

    No step of this can raise: building a User-Agent must never block an HTTP call.
    """
    global _SOCRADAR_UA_CACHE
    if _SOCRADAR_UA_CACHE:
        return _SOCRADAR_UA_CACHE
    splunk_ver = "unknown"
    try:
        vf = os.path.join(os.environ.get("SPLUNK_HOME", ""), "etc", "splunk.version")
        with open(vf) as fh:
            for line in fh:
                if line.startswith("VERSION="):
                    splunk_ver = line.split("=", 1)[1].strip() or "unknown"
                    break
    except Exception:
        pass
    # `requests` is NOT a module-level import in every file that uses this helper
    # (two of them import it inside a function), so read the version through a
    # local import instead of a module-scope lookup.
    req_ver = "unknown"
    try:
        import requests as _rq
        req_ver = _rq.__version__
    except Exception:
        pass
    _SOCRADAR_UA_CACHE = (
        "SOCRadar-Splunk-TA-incidents-mssp/1.0.0 (build 23; Splunk/%s; python-requests/%s)"
        % (splunk_ver, req_ver))
    return _SOCRADAR_UA_CACHE


# Debug log file
DEBUG_LOG = os.path.join(os.environ.get("SPLUNK_HOME", "/opt/splunk"), "var", "log", "socradar", "status_update_mssp_log.txt")

# Splunk stored-credential field separator. The AOB/solnlib credential layer
# chunks a stanza's encrypted blob across multiple storage/passwords stanzas
# whose username is ``<stanza><SEP><index>`` (index starts at 1), then appends
# one extra stanza holding END_MARK to signal the end of the value.
CRED_SEP = "``splunk_cred_sep``"
END_MARK = (
    "``splunk_cred_sep``S``splunk_cred_sep``P``splunk_cred_sep``L``splunk_cred_sep``"
    "U``splunk_cred_sep``N``splunk_cred_sep``K``splunk_cred_sep``"
)
APP_NAME = "TA-socradar-incidents-mssp"


def log_debug(msg):
    try:
        os.makedirs(os.path.dirname(DEBUG_LOG), exist_ok=True)
        with open(DEBUG_LOG, 'a') as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except Exception:
        # never let logging break the command
        pass


_KNOWN_SECRETS = []


def _register_secret(value):
    """Remember a credential value so every _scrub() call redacts it, even from call
    sites that forget to pass it explicitly (EXP-0286-b4: this file's own exception
    handler used to run a separate, narrower inline regex instead of calling _scrub()
    at all -- a dead-code miss that a plumbed secret= parameter alone cannot prevent
    if a future call site makes the same mistake). Call once, right after reading.
    EXP-0286-b5 (adversary live-fire finding): also remember the repr()-escaped form.
    requests' own InvalidHeader message embeds the offending header value via
    f"...{header_part!r}", which backslash-escapes control characters (\\t/\\n/\\r) but
    leaves every other character byte-identical -- so a raw secret containing one of
    those never appears verbatim, yet everything except the escaped byte still does.
    repr(value)[1:-1] is always just the quoted body (Python's repr wraps the WHOLE
    string in one quote pair), so registering it too closes that gap the same way.
    EXP-0286-b6 (adversary live-fire finding, round 2): this file builds its URL with
    an f-string ?key=<value>; requests percent-encodes it (requote_uri) before the
    request ever leaves, and that ENCODED form -- not the raw value -- is what shows
    up in a subsequent exception's message. requote_uri has TWO safe-sets depending on
    whether the value already contains a literal '%' followed by non-hex (its
    unquote_unreserved pre-pass raises InvalidURL and it falls back to a set that does
    NOT leave '%' alone): "!#$%&'()*+,/:;=?@[]~" (normal path) vs "!#$&'()*+,/:;=?@[]~"
    (fallback path). Either way it leaves '/&/)/, byte-identical -- exactly what the
    regex backstop below treats as a delimiter. Registering both safe-sets plus a
    fully-escaped (safe="") catch-all closes this the same content-independent way."""
    if value and str(value) not in _KNOWN_SECRETS:
        v = str(value)
        _KNOWN_SECRETS.append(v)
        escaped = repr(v)[1:-1]
        if escaped and escaped != v and escaped not in _KNOWN_SECRETS:
            _KNOWN_SECRETS.append(escaped)
        for _safe in ("!#$%&'()*+,/:;=?@[]~", "!#$&'()*+,/:;=?@[]~", ""):
            try:
                pct = _urlquote(v, safe=_safe)
            except Exception:
                continue
            if pct and pct != v and pct not in _KNOWN_SECRETS:
                _KNOWN_SECRETS.append(pct)
    _install_log_redaction()


class _SecretRedactingFilter(logging.Filter):
    """EXP-0286-b7 (live-fire finding in a real Splunk Docker container, 2026-08-26):
    urllib3's OWN retry machinery (urllib3.connectionpool, e.g. the "Retrying
    (Retry(...)) after connection broken by ..." WARNING) logs the full request URL --
    including the ?key=<secret> query string -- through Python's stdlib logging module
    directly. It never raises an exception this file catches and never passes through
    _scrub(), so it bypassed every defense above entirely; confirmed live in this app's
    own collector log file, sitting right next to a correctly-redacted line from this
    file's own helper.log_error() call on the SAME failed request. A logging.Filter
    attached to a LOGGER only ever sees records that ORIGINATE at that logger --
    propagation carries a record up to ancestor HANDLERS, never through ancestor
    loggers' own filters -- so a filter attached to the root logger would be a silent
    no-op for a record born in urllib3.connectionpool (verified with an isolated repro
    before shipping this, to avoid re-learning that the hard way in production).
    Filters attached to HANDLERS, by contrast, see every record that reaches that
    handler regardless of where it originated, which is what makes this the
    content-independent class-killer for third-party/vendored-library log output --
    the same principle as _register_secret() above, one layer up the pipeline."""

    def filter(self, record):
        try:
            record.msg = _scrub(record.getMessage())
            record.args = ()
            if getattr(record, "exc_info", None):
                record.exc_text = _scrub(logging.Formatter().formatException(record.exc_info))
        except Exception:
            pass
        return True


def _install_log_redaction():
    """Two layers, both cheap and idempotent -- safe to call every time a secret is
    registered, since a Splunk-managed log handler may not exist yet at import time.
    (1) Raise urllib3's own effective log level above WARNING so it never even
    constructs the retry message: getEffectiveLevel() is inherited, so setting it once
    on the "urllib3" logger silences every urllib3.* sub-logger (connectionpool,
    poolmanager, ...) in one call. This app's own log_error(_scrub(e)) call already
    reports the terminal failure after retries are exhausted, so no operational signal
    is lost -- only the noisy, unredacted per-attempt retry WARNING is dropped.
    (2) Attach a redacting Filter to every HANDLER already registered on the root
    logger -- the backstop for any other vendored library that logs at ERROR or above
    (survives layer 1) or that this app doesn't yet know to silence by logger name."""
    try:
        logging.getLogger("urllib3").setLevel(logging.ERROR)
    except Exception:
        pass
    try:
        for _h in logging.getLogger().handlers:
            if not any(isinstance(_f, _SecretRedactingFilter) for _f in getattr(_h, "filters", [])):
                _h.addFilter(_SecretRedactingFilter())
    except Exception:
        pass


def _scrub(text, secret=None):
    """Redact secrets before logging. A requests/urllib3 network error stringifies the
    full request URL, which contains ?key=<secret>; it can also stringify a credential
    -embedded proxy URL (an OS-level HTTPS_PROXY/HTTP_PROXY env var honored via
    trust_env=True). Two layers: (1) every _register_secret()-ed value is literal
    str.replace()d -- immune to whatever characters the secret contains; (2) a regex
    backstop (key= query param, //user:pass@host userinfo) for secrets this process
    never reads itself. EXP-0286-b4: DOTALL so '.' also matches whitespace/newline --
    a character-class approach (even one excluding only '/') either anchors on the
    wrong '@' or skips the match once the secret contains an excluded character."""
    try:
        s = str(text)
        secrets = list(_KNOWN_SECRETS)
        if secret:
            secrets.append(str(secret))
        for sec in secrets:
            if sec:
                s = s.replace(sec, "***REDACTED***")
        s = re.sub(r'([?&][Kk]ey=)[^\s&"\'),]+', r'\1<redacted>', s)
        s = re.sub(r'//.+@', '//***:***@', s, flags=re.DOTALL)
        # EXP-0286-b4 (live-fire finding): CPython's http.client._validate_host()
        # control-character preflight (CVE-2019-9740/18348 mitigation) can raise
        # InvalidURL with a small unpredictable fragment of a malformed credential
        # baked into its OWN message, before a //user:pass@ string ever exists for
        # the layers above to catch. Confirmed live: a whitespace-containing proxy
        # password produced "URL can't contain control characters. 'ss w' (found at
        # least ' ')". Redact by the stdlib message template, not by secret value.
        s = re.sub(r"URL can't contain control characters\..*",
                    "URL can't contain control characters. <redacted>", s)
        return s
    except Exception:
        return "<scrub failed>"


def resolve_company_stanza(target_company_id):
    """MSSP: return the input stanza whose Multi-Tenant credential covers this alarm.

    One Multi-Tenant input serves EVERY entitled company, so the stanza is not
    selected by company any more - the key is the same for all of them. What still
    matters is that a configured Multi-Tenant input exists at all: without one there
    is no credential to send, and guessing is exactly the tenant-boundary mistake
    this add-on exists to prevent. The argument is kept so the caller keeps asserting
    that an alarm actually carries a company before anything is sent.
    """
    if not str(target_company_id or '').strip():
        return None
    splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
    conf_file = os.path.join(
        splunk_home, 'etc', 'apps', APP_NAME, 'local', 'inputs.conf'
    )
    current = None
    stanzas = {}
    order = []
    if os.path.exists(conf_file):
        with open(conf_file, 'r') as f:
            for raw in f:
                line = raw.strip()
                if line.startswith('[') and line.endswith(']'):
                    current = line[1:-1].strip()
                    if current not in stanzas:
                        stanzas[current] = {}
                        order.append(current)
                elif current and '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    stanzas[current][k.strip()] = v.strip()
    for name in order:
        conf = stanzas[name]
        if not conf.get('multi_tenant_id'):
            continue
        if str(conf.get('disabled', '0')).strip().lower() in ('1', 'true'):
            continue
        return name
    return None


def _parse_cred_blob(blob):
    """Extract socradar_api_key from a reassembled credential blob.

    The AOB/solnlib credential layer stores the stanza's encrypted fields as a
    JSON object: ``{"socradar_api_key": "<value>"}``. Some older layouts use a
    SEP-flattened ``field<SEP>val`` form, so handle that as a fallback. Never
    log the value.
    """
    if not blob:
        return None

    # Primary: JSON object (AOB/solnlib format)
    try:
        obj = json.loads(blob)
        if isinstance(obj, dict) and obj.get('socradar_api_key'):
            return obj['socradar_api_key']
    except Exception:
        pass

    # Fallback: SEP-flattened key/value pairs
    if CRED_SEP in blob:
        parts = blob.split(CRED_SEP)
        if len(parts) % 2 == 0:
            pairs = {parts[i]: parts[i + 1] for i in range(0, len(parts), 2)}
            if pairs.get('socradar_api_key'):
                return pairs['socradar_api_key']

    return None


def get_api_key(session_key, app, stanza_name):
    """Retrieve the encrypted socradar_api_key from storage/passwords.

    The encrypted input fields are stored by the AOB/solnlib credential layer
    under realm ``__REST_CREDENTIAL__#<app>#...`` with the *input stanza name*
    as the username (chunked as ``<stanza><SEP><index>`` starting at index 1,
    terminated by an END_MARK stanza). Reassemble the chunks (stopping at
    END_MARK), then parse the JSON blob. Returns the key, or None.
    NEVER logs the key value.
    """
    if not session_key:
        return None

    import splunk.rest as rest

    url = '/servicesNS/nobody/%s/storage/passwords?output_mode=json&count=-1' % app
    try:
        resp, content = rest.simpleRequest(
            url, sessionKey=session_key, method='GET', raiseAllErrors=False
        )
    except Exception as e:
        log_debug(f"storage/passwords request error: {_scrub(e)}")
        return None

    if isinstance(content, bytes):
        content = content.decode('utf-8', errors='replace')

    try:
        data = json.loads(content)
    except Exception as e:
        log_debug(f"storage/passwords parse error: {_scrub(e)}")
        return None

    prefix = "__REST_CREDENTIAL__#%s#" % app

    # The cred username base is the input NAME only, while inputs.conf stanzas
    # are "<scheme>://<name>" (e.g. socradar_incidents_mssp_collector://my_input).
    # Match on the name part after '://' so the prefix doesn't break the lookup.
    want = stanza_name.split('://', 1)[-1] if stanza_name else None

    # Group chunks by (realm, username-base). The username base is the input
    # name; only keep entries whose base matches the configured input.
    groups = {}
    for entry in data.get('entry', []):
        c = entry.get('content', {}) or {}
        realm = c.get('realm', '') or ''
        if not realm.startswith(prefix):
            continue
        uname = c.get('username', '') or ''
        base = uname.split(CRED_SEP)[0]
        if want and base != want:
            continue
        clear = c.get('clear_password', '') or ''
        if CRED_SEP in uname:
            try:
                idx = int(uname.rsplit(CRED_SEP, 1)[1])
            except ValueError:
                idx = 0
        else:
            idx = 0
        groups.setdefault((realm, base), {})[idx] = clear

    for (realm, base), chunks in groups.items():
        blob = ""
        for idx in sorted(chunks.keys()):
            piece = chunks[idx]
            if piece == END_MARK:
                break
            blob += piece
        key = _parse_cred_blob(blob)
        if key:
            return key
    return None


def parse_session_key(raw):
    """Extract the Splunk session key from the input header block.

    With enableheader/passauth the header arrives on stdin two ways:
        authString:<auth>...<authToken>KEY</authToken></auth>
        sessionKey:KEY
    Try the authString XML <authToken> first, then the sessionKey: line; fall
    back to empty. NEVER log the value.
    """
    if not raw:
        return ""
    m = re.search(r'<authToken>(.*?)</authToken>', raw, re.S)
    if m and m.group(1).strip():
        return m.group(1).strip()
    for line in raw.splitlines():
        if line.startswith('sessionKey:'):
            val = line.split(':', 1)[1].strip()
            if val:
                return val
    return ""


def parse_alarm_fields(raw):
    """Extract alarm_id / new_status from the piped search body.

    The Manage Alarm Status dashboard pipes a single row carrying
    ``input_data = "alarm_id=<id>,new_status=<status>"``. Scan each line for the
    alarm_id= token (this works even though the CSV-quoted input_data value
    embeds a comma) -- the original 1.9.27 method. Fall back to a direct
    alarm_id / new_status CSV column if the token form is absent.
    """
    alarm_id = ""
    new_status = ""
    company_id = ""
    lines = raw.splitlines()

    # Primary: original line-scan for the input_data token.
    for line in lines:
        if 'alarm_id=' in line:
            for part in line.split(','):
                if 'alarm_id=' in part:
                    alarm_id = part.split('=', 1)[1].strip().strip('"')
                elif 'new_status=' in part:
                    new_status = part.split('=', 1)[1].strip().strip('"')
                elif 'company_id=' in part:
                    # MSSP: the dashboard pipes the alarm's OWN company so the
                    # update never lands on another tenant.
                    company_id = part.split('=', 1)[1].strip().strip('"')
        if alarm_id:
            break

    # Fallback: direct alarm_id / new_status CSV columns.
    if not alarm_id:
        for i, line in enumerate(lines):
            cols = [c.strip().strip('"') for c in line.split(',')]
            if 'alarm_id' in cols and i + 1 < len(lines):
                vals = [c.strip().strip('"') for c in lines[i + 1].split(',')]
                ai = cols.index('alarm_id')
                if ai < len(vals):
                    alarm_id = vals[ai]
                if 'new_status' in cols:
                    ni = cols.index('new_status')
                    if ni < len(vals):
                        new_status = vals[ni]
                break

    return alarm_id, new_status, company_id


def main():
    import requests

    # Simple-protocol command: emit CSV header first.
    print("alarm_id,status,result,message,time")

    try:
        log_debug("=== NEW STATUS UPDATE REQUEST ===")

        # Read the whole chunk ONCE. With enableheader/passauth the header block
        # (carrying the session key) AND the piped CSV results arrive together
        # on stdin. getOrganizedResults() consumed stdin but returned EMPTY
        # results here, so parse both straight out of the raw text.
        raw = sys.stdin.read()
        session_key = parse_session_key(raw)
        alarm_id, new_status, piped_company_id = parse_alarm_fields(raw)
        log_debug(
            f"Parsed: alarm_id={alarm_id}, new_status={new_status}, "
            f"have_session_key={bool(session_key)}"
        )

        if not alarm_id:
            print("NONE,No alarm selected,WAITING,Enter an alarm ID," + str(int(time.time())))
            return

        # Read non-secret config from inputs.conf, secret key from storage/passwords.
        if str(piped_company_id).strip().upper() == 'UNKNOWN':
            log_debug('Alarm carries no company (UNKNOWN); refusing to send an update.')
            print(
                f'{alarm_id},Error,ERROR,This alarm arrived from SOCRadar without a '
                f'company, so it cannot be updated from Splunk,' + str(int(time.time()))
            )
            return
        if piped_company_id:
            company_id = piped_company_id
            stanza_name = resolve_company_stanza(piped_company_id)
            if not stanza_name:
                # MSSP fail-CLOSED. Falling back to another stanza here would put
                # one customer's API key inside a request scoped to a DIFFERENT
                # customer's company path - a tenant-boundary crossing in the very
                # add-on whose purpose is tenant separation. Refuse instead.
                log_debug(
                    'No enabled Multi-Tenant input is configured; refusing to send an '
                    'alarm update without a credential.'
                )
                print(
                    f'{alarm_id},Error,ERROR,No enabled SOCRadar Multi-Tenant input is '
                    f'configured - create one first,' + str(int(time.time()))
                )
                return
        else:
            # MSSP fail-CLOSED #2: an EMPTY company is NOT a "use the default
            # tenant" signal - an MSSP install has no default tenant. The
            # inherited single-tenant lookup (last stanza in inputs.conf wins)
            # would send one company's alarm with ANOTHER company's API key.
            # Reachable in practice: the dashboard's Company dropdown is fed by a
            # -30d@d search, so it comes back empty on a fresh install or for a
            # quiet tenant, and the token then renders as an empty string.
            log_debug(
                'No company was piped with the alarm; refusing to guess a tenant.'
            )
            print(
                f'{alarm_id},Error,ERROR,No company was supplied with the alarm - '
                f'select a company (or click the alarm row) and try again,'
                + str(int(time.time()))
            )
            return
        api_key = get_api_key(session_key, APP_NAME, stanza_name)
        _register_secret(api_key)

        if not company_id or not api_key:
            log_debug(
                f"Missing credentials (company_id={bool(company_id)}, "
                f"api_key_present={bool(api_key)})"
            )
            print(f"{alarm_id},Error,ERROR,Missing credentials," + str(int(time.time())))
            return

        # Status mapping
        status_map = {
            '0': 'Open',
            '1': 'OnHold-Investigating',
            '2': 'Closed-Resolved',
            '3': 'OnHold-Pending',
            '5': 'OnHold-Legal',
            '9': 'Closed-FalsePositive',
            '10': 'Closed-Duplicate',
            '11': 'Closed-ProcessedInternally',
            '12': 'Closed-Mitigated',
            '13': 'Closed-NotApplicable'
        }

        status_name = status_map.get(new_status, f'Status-{new_status}')

        # Make API call
        url = f"https://platform.socradar.com/api/company/{company_id}/alarms/status/change"
        payload = {
            "status": new_status,
            "alarm_ids": alarm_id,
            "comments": f"Updated via Splunk to: {status_name}"
        }

        # The URL no longer carries the key at all (it moved to the API-Key header),
        # so there is nothing secret left in it to truncate away.
        log_debug(f"Calling API: {url[:50]}...")

        response = requests.post(url, json=payload,
                                 headers={"Content-Type": "application/json",
                                          "API-Key": api_key,
                                          "User-Agent": socradar_user_agent()},
                                 timeout=30)
        response_data = response.json()

        log_debug(f"API Response: {response.status_code}")

        if response.status_code == 200 and response_data.get('is_success', False):
            print(f"{alarm_id},{status_name},SUCCESS,Updated successfully," + str(int(time.time())))
            # The status is now changed at SOCRadar. The modular-input collector
            # detects the status change on its next poll and re-indexes the FULL
            # alarm (with the new status) into the socradar_incidents_mssp index, so the
            # dashboard reflects it within one collection cycle.
            log_debug(f"Status change SUCCESS for {alarm_id} -> {status_name}; dashboard updates on next collector poll.")
        else:
            msg = _scrub(str(response_data.get('message', 'Update failed'))).replace(',', ';')
            if response.status_code in (401, 403):
                msg += ' (HTTP ' + str(response.status_code) + ': the Multi-Tenant key may not be '
                msg += 'authorized to update alarms for this company)'
            print(f"{alarm_id},{status_name},FAILED,{msg}," + str(int(time.time())))
            log_debug(f"Update failed: {msg}")

    except Exception as e:
        # EXP-0286-b4: route through the module-level _scrub(), not a separate inline
        # regex -- a second redaction path here previously never picked up the
        # //user:pass@ proxy-userinfo case (or any future _scrub() fix) at all.
        _safe = _scrub(e)
        log_debug(f"EXCEPTION: {_safe}")
        print(f"ERROR,Error,ERROR,{_safe.replace(',', ';')}," + str(int(time.time())))


if __name__ == '__main__':
    main()
