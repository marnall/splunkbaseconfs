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


DEBUG_LOG = os.path.join(os.environ.get("SPLUNK_HOME", "/opt/splunk"), "var", "log", "socradar", "ioc_enrichment_mssp_log.txt")

# AOB/solnlib credential layer field separator (chunked encrypted blob).
CRED_SEP = "``splunk_cred_sep``"
END_MARK = (
    "``splunk_cred_sep``S``splunk_cred_sep``P``splunk_cred_sep``L``splunk_cred_sep``"
    "U``splunk_cred_sep``N``splunk_cred_sep``K``splunk_cred_sep``"
)
APP_NAME = "TA-socradar-incidents-mssp"
IOC_URL = "https://platform.socradar.com/api/ioc_enrichment/get/indicator_details"
API_TIMEOUT_SECONDS = 30
# Request the full enrichment payload (matches the proven SOCRadar postman collection).
IOC_FIELDS = ["indicator_details", "indicator_history", "indicator_relations"]
MAX_HISTORY = 1000  # KV history collection cap: prune oldest records beyond this


def log_debug(msg):
    try:
        os.makedirs(os.path.dirname(DEBUG_LOG), exist_ok=True)
        with open(DEBUG_LOG, 'a') as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except Exception:
        pass


_KNOWN_SECRETS = []


def _register_secret(value):
    """Remember a credential value so every _scrub() call redacts it, even from call
    sites that forget to pass it explicitly (EXP-0286-b4). Call once, right after
    resolving the api_key.
    EXP-0286-b5 (adversary live-fire finding): also remember the repr()-escaped form.
    requests' own InvalidHeader message embeds the offending header value via
    f"...{header_part!r}", which backslash-escapes control characters (\\t/\\n/\\r) but
    leaves every other character byte-identical -- so a raw secret containing one of
    those never appears verbatim, yet everything except the escaped byte still does.
    repr(value)[1:-1] is always just the quoted body (Python's repr wraps the WHOLE
    string in one quote pair), so registering it too closes that gap the same way.
    EXP-0286-b6 (adversary live-fire finding, round 2): a URL built with an f-string
    ?key=<value> gets percent-encoded by requests' own requote_uri() before it ever
    reaches the wire/exception text -- a THIRD wire-form, distinct from both the raw
    value and the repr()-escape. requote_uri has TWO safe-sets depending on whether the
    value already contains a literal '%' followed by non-hex (its unquote_unreserved
    pre-pass raises InvalidURL and it falls back to a set that does NOT leave '%'
    alone): "!#$%&'()*+,/:;=?@[]~" (normal path) vs "!#$&'()*+,/:;=?@[]~" (fallback
    path). This file's own IOC call uses an API-Key header (not a key= URL param) so
    the vector isn't reachable here today, but registering both safe-sets plus a
    fully-escaped (safe="") catch-all keeps every _register_secret() call site
    uniformly immune, the same content-independent way."""
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
    """Redact secrets before logging. A requests/urllib3 error can stringify a
    key= query param, an API-Key header value, or a credential-embedded proxy URL
    (an OS-level HTTPS_PROXY/HTTP_PROXY env var honored via trust_env=True). Two
    layers: (1) every _register_secret()-ed value is literal str.replace()d --
    immune to whatever characters the secret contains; (2) a regex backstop for
    secrets this process never reads itself. EXP-0286-b4: DOTALL so '.' also
    matches whitespace/newline -- a character-class approach (even one excluding
    only '/') either anchors on the wrong '@' or skips the match once the secret
    contains an excluded character."""
    try:
        s = str(text)
        secrets = list(_KNOWN_SECRETS)
        if secret:
            secrets.append(str(secret))
        for sec in secrets:
            if sec:
                s = s.replace(sec, "***REDACTED***")
        s = re.sub(r'([?&][Kk]ey=)[^\s&"\'),]+', r'\1<redacted>', s)
        s = re.sub(r'(API-Key[\'"]?\s*[:=]\s*[\'"]?)[^\s"\',&]{12,}', r'\1<redacted>', s)
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


def read_inputs_conf_stanza():
    """Return the input stanza name from local/inputs.conf (locates the encrypted credential)."""
    splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
    conf_file = os.path.join(splunk_home, 'etc', 'apps', APP_NAME, 'local', 'inputs.conf')
    stanza_name = None
    if os.path.exists(conf_file):
        with open(conf_file, 'r') as f:
            for raw in f:
                line = raw.strip()
                if line.startswith('[') and line.endswith(']'):
                    stanza_name = line[1:-1].strip()
    return stanza_name


def _blob_field(blob, field):
    """Extract a named field from a reassembled credential blob (JSON or SEP-flattened)."""
    if not blob:
        return None
    try:
        obj = json.loads(blob)
        if isinstance(obj, dict) and obj.get(field):
            return obj[field]
    except Exception:
        pass
    if CRED_SEP in blob:
        parts = blob.split(CRED_SEP)
        if len(parts) % 2 == 0:
            pairs = {parts[i]: parts[i + 1] for i in range(0, len(parts), 2)}
            if pairs.get(field):
                return pairs[field]
    return None


def get_cred_field(session_key, app, stanza_name, field, realm_suffix=None):
    """Retrieve an encrypted input field (e.g. ioc_api_key or socradar_api_key) from
    storage/passwords (AOB/solnlib layout). Reassemble the chunked blob, parse, return the
    value or None. NEVER logs the value.
    realm_suffix: when given, only credentials whose realm ends with it are considered --
    used to pin the GLOBAL settings lookup to configs/conf-ta_socradar_incidents_mssp_settings,
    so an input that happens to be named 'additional_parameters' can never shadow it."""
    if not session_key:
        return None
    import splunk.rest as rest
    url = '/servicesNS/nobody/%s/storage/passwords?output_mode=json&count=-1' % app
    try:
        resp, content = rest.simpleRequest(url, sessionKey=session_key, method='GET', raiseAllErrors=False)
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
    want = stanza_name.split('://', 1)[-1] if stanza_name else None
    groups = {}
    for entry in data.get('entry', []):
        c = entry.get('content', {}) or {}
        realm = c.get('realm', '') or ''
        if not realm.startswith(prefix):
            continue
        if realm_suffix and not realm.endswith(realm_suffix):
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
        val = _blob_field(blob, field)
        if val:
            return val
    return None


def parse_session_key(raw):
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


def parse_indicator(raw):
    """Extract the indicator from the piped search body (| eval input_data="indicator=...")."""
    indicator = ""
    lines = [l for l in raw.splitlines() if l.strip()]
    for line in lines:
        if 'indicator=' in line:
            for part in line.split(','):
                if 'indicator=' in part:
                    indicator = part.split('=', 1)[1].strip().strip('"')
                    break
        if indicator:
            return indicator
    for i, line in enumerate(lines):
        cols = [c.strip().strip('"') for c in line.split(',')]
        if 'indicator' in cols and i + 1 < len(lines):
            vals = [c.strip().strip('"') for c in lines[i + 1].split(',')]
            ci = cols.index('indicator')
            if ci < len(vals):
                indicator = vals[ci]
                break
    return indicator


def save_enrichment(session_key, payload):
    """Persist one enrichment to a KV-store collection so the dashboard can show a HISTORY of
    past lookups. KV store is search-head-local and works on Splunk Cloud -- a receivers/simple
    POST from a SEARCH command does NOT route to the Cloud indexer tier, so an index-based
    history would be silently empty on Cloud. Best-effort: a failed save must never break the
    command. The API key is NEVER part of the payload."""
    if not session_key:
        return
    base = '/servicesNS/nobody/%s/storage/collections/data/ioc_enrichment_mssp_history' % APP_NAME
    try:
        import splunk.rest as rest
        rest.simpleRequest(base + '?output_mode=json', sessionKey=session_key, method='POST',
                           jsonargs=json.dumps(payload), raiseAllErrors=False)
    except Exception as e:
        log_debug(f"save enrichment failed (non-fatal): {_scrub(e)}")
        return
    # Bound growth: keep the most-recent MAX_HISTORY records, delete the rest (best-effort).
    try:
        import splunk.rest as rest
        resp, content = rest.simpleRequest(base + '?fields=_key,enriched_at&limit=50000&output_mode=json',
                                           sessionKey=session_key, method='GET', raiseAllErrors=False)
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='replace')
        rows = json.loads(content)
        if not isinstance(rows, list):
            rows = []
        if len(rows) > MAX_HISTORY:
            rows.sort(key=lambda r: str(r.get('enriched_at', '')), reverse=True)
            for r in rows[MAX_HISTORY:]:
                k = r.get('_key')
                if k:
                    rest.simpleRequest('%s/%s' % (base, k), sessionKey=session_key, method='DELETE', raiseAllErrors=False)
    except Exception as e:
        log_debug(f"prune history failed (non-fatal): {_scrub(e)}")


def _csv(v):
    return str(v).replace(',', ';').replace('\n', ' ').replace('\r', ' ').replace('"', "'")


def main():
    import requests
    import csv

    # One wide, self-describing row per lookup. Column order is fixed so the dashboard
    # can pick a summary subset, transpose for a key/value detail panel, or show the
    # full raw_json verbatim. emit() fills any unset column with "" so every row has the
    # same width (no more manual comma-counting -> no ragged-row bugs).
    COLUMNS = [
        "indicator", "entity_type", "score", "signal_strength", "country", "region",
        "categories", "activity_1d", "activity_7d", "activity_30d", "activity_90d",
        "threat_actors", "malwares", "campaign", "industries", "mitre",
        "as_owner", "asn", "cidr", "ports", "first_seen", "last_seen", "is_whitelisted",
        "abuse_confidence", "vt_link", "urlhaus_link", "alienvault_link",
        "feed_sources", "relations_count", "premium_feeds_count",
        "summary", "remaining_credit", "result", "message", "raw_json", "time",
    ]
    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow(COLUMNS)

    def clean(v):
        # csv.writer quotes commas/quotes for us; only collapse CR/LF so a stray newline
        # inside a text field can never desync the streamed-CSV row protocol.
        return str(v).replace("\r", " ").replace("\n", " ")

    def emit(**kw):
        w.writerow([clean(kw.get(c, "")) for c in COLUMNS])

    def jn(x):
        if isinstance(x, (list, tuple)):
            return "; ".join(str(i) for i in x if i not in (None, ""))
        return "" if x is None else str(x)

    try:
        log_debug("=== NEW IOC ENRICHMENT REQUEST ===")
        raw = sys.stdin.read()
        session_key = parse_session_key(raw)
        indicator = parse_indicator(raw)
        log_debug(f"Parsed: indicator={indicator!r}, have_session_key={bool(session_key)}")

        now = str(int(time.time()))
        if not indicator:
            emit(indicator="", result="WAITING",
                 message="Enter an indicator (IP / domain / hash / URL) and click Submit", time=now)
            return

        stanza_name = read_inputs_conf_stanza()
        # IOC Enrichment is a separate "advanced" API tier -- many accounts issue a distinct
        # key for it, so the incidents key alone often gets 402.
        # Lookup order (deterministic): 1) GLOBAL IOC key from Configuration > Add-on Settings
        # (stored under the 'additional_parameters' stanza of the settings conf; the lookup is
        # PINNED to the settings realm via realm_suffix, so even an input literally named
        # 'additional_parameters' cannot shadow it - set once, app-wide, always wins);
        # 2) legacy per-input ioc_api_key (kept for upgrades from dev builds that had the field
        # on the input form); 3) an input's incidents key (402 if it lacks the IOC tier).
        api_key = (get_cred_field(session_key, APP_NAME, "additional_parameters", "ioc_api_key",
                                  realm_suffix="configs/conf-ta_socradar_incidents_mssp_settings")
                   or get_cred_field(session_key, APP_NAME, stanza_name, "ioc_api_key")
                   or get_cred_field(session_key, APP_NAME, None, "ioc_api_key")
                   or get_cred_field(session_key, APP_NAME, stanza_name, "socradar_api_key")
                   or get_cred_field(session_key, APP_NAME, None, "socradar_api_key"))
        _register_secret(api_key)
        if not api_key:
            emit(indicator=indicator, result="ERROR",
                 message="No API key found (set the IOC Enrichment API Key under Configuration > Add-on Settings, or configure an input)", time=now)
            log_debug("Missing api_key (ioc_api_key + socradar_api_key both empty)")
            return

        # Auth via the API-Key header (proven by the SOCRadar postman collection; keeps the key
        # out of the URL so it cannot leak into request logs). Body carries indicator + fields.
        try:
            response = requests.post(IOC_URL,
                                     json={"indicator": indicator, "fields": IOC_FIELDS},
                                     headers={"User-Agent": socradar_user_agent(), "Content-Type": "application/json", "API-Key": api_key},
                                     timeout=API_TIMEOUT_SECONDS)
        except Exception as e:
            emit(indicator=indicator, result="ERROR", message=_scrub(e), time=now)
            log_debug(f"request error: {_scrub(e)}")
            return

        log_debug(f"IOC API response: {response.status_code}")

        if response.status_code == 401:
            emit(indicator=indicator, result="ERROR",
                 message="Unauthorized (401) - check the IOC Enrichment API Key", time=now)
            return
        if response.status_code == 402:
            emit(indicator=indicator, result="ERROR",
                 message="No IOC Enrichment credit/entitlement (402) - this key lacks the IOC tier", time=now)
            return

        try:
            r = response.json()
        except Exception as e:
            emit(indicator=indicator, result="ERROR",
                 message=f"Non-JSON response (HTTP {response.status_code})", time=now)
            log_debug(f"json parse error: {_scrub(e)}")
            return

        raw_json = json.dumps(r, ensure_ascii=False)

        # Locate the enrichment object. Live API returns it at TOP LEVEL; saved captures
        # used a "body" wrapper; the async/not-ready envelope nests under "data" (or null).
        body = r
        if isinstance(r, dict):
            if isinstance(r.get("body"), dict):
                body = r["body"]
            elif isinstance(r.get("data"), dict):
                body = r["data"]
        if not isinstance(body, dict):
            body = {}

        # Envelope with no enrichment payload -> URL / first-time lookup returns HTTP 202
        # {"data": null, "is_success": false, "response_code": 202, "message":
        # "IOC details are being enriched ... retry in a few minutes. No credits charged."}.
        # Surface that message instead of a blank row (this was the "URL shows nothing" bug).
        if not body.get("details") and not body.get("categorization"):
            msg = (r.get("message") if isinstance(r, dict) else "") or "No enrichment data returned"
            code = r.get("response_code") if isinstance(r, dict) else None
            low = str(msg).lower()
            if code == 202 or "retry" in low or "shortly" in low or "being enriched" in low:
                res = "PENDING"
            else:
                res = "INFO"
            emit(indicator=indicator, result=res, message=msg, raw_json=raw_json, time=now)
            log_debug(f"Envelope response for {indicator}: code={code} result={res}")
            return

        details = body.get("details", {}) or {}
        top = body.get("top_classifications", {}) or {}
        cats = body.get("categorization", {}) or {}
        acts = body.get("activity_label_dict", {}) or {}
        extra = details.get("extra_info", {}) or {}

        score = details.get("score")
        if isinstance(score, (list, tuple)) and score:
            score = score[0]
        true_cats = [k for k, v in cats.items() if v is True]
        threat_actors = top.get("threat_actors") or []
        malwares = top.get("malwares") or []
        industries = top.get("industries") or []
        country = top.get("country") or details.get("country_list") or ""
        if isinstance(country, (list, tuple)):
            country = jn(country)
        mitre = []
        dtags = details.get("tags", {}) or {}
        if isinstance(dtags, dict):
            for m in (dtags.get("MITRE_ATTCK") or []):
                if isinstance(m, dict) and m.get("tag"):
                    mitre.append(m["tag"])
        summary = body.get("socradar_copilot:ioc_agent") or ""
        if isinstance(summary, str) and len(summary) > 1200:
            summary = summary[:1200] + "..."
        remaining = (body.get("api_credit", {}) or {}).get("remaining_credit", "")
        signal = details.get("ioc_signal_strength") or body.get("ioc_signal_strength") or ""
        relations = r.get("relations") if isinstance(r, dict) else None
        premium = r.get("premium_feeds") if isinstance(r, dict) else None

        fields = {
            "indicator": indicator,
            "entity_type": details.get("entity_type") or details.get("object_type") or "",
            "score": score if score is not None else "",
            "signal_strength": signal,
            "country": country,
            "region": top.get("region") or "",
            "categories": jn(true_cats),
            "activity_1d": acts.get("last_1_day") or "",
            "activity_7d": acts.get("last_7_days") or "",
            "activity_30d": acts.get("last_30_days") or "",
            "activity_90d": acts.get("last_90_days") or "",
            "threat_actors": jn(threat_actors),
            "malwares": jn(malwares),
            "campaign": top.get("campaign") or "",
            "industries": jn(industries),
            "mitre": jn(mitre),
            "as_owner": details.get("as_owner") or "",
            "asn": details.get("asn_name") or details.get("asn_code") or "",
            "cidr": details.get("cidr") or "",
            "ports": jn(details.get("ports") or []),
            "first_seen": details.get("first_seen_date") or "",
            "last_seen": details.get("last_seen_date") or "",
            "is_whitelisted": details.get("is_whitelisted"),
            "abuse_confidence": extra.get("abuse_confidence_score")
                if extra.get("abuse_confidence_score") is not None else "",
            "vt_link": details.get("vt_link") or "",
            "urlhaus_link": details.get("urlhaus_link") or "",
            "alienvault_link": details.get("alienvault_link") or "",
            "feed_sources": jn(details.get("feed_source_list") or []),
            "relations_count": len(relations) if isinstance(relations, list) else "",
            "premium_feeds_count": len(premium) if isinstance(premium, list) else "",
            "summary": summary,
            "remaining_credit": remaining,
            "result": "SUCCESS",
            "message": "Enriched",
            "raw_json": raw_json,
            "time": now,
        }

        # Persist a compact record so the dashboard HISTORY panel keeps working (no api_key).
        save_enrichment(session_key, {
            "indicator": indicator,
            "score": fields["score"],
            "signal_strength": signal,
            "categories": jn(true_cats),
            "country": country,
            "threat_actors": jn(threat_actors),
            "malwares": jn(malwares),
            "mitre": jn(mitre),
            "remaining_credit": remaining,
            "result": "SUCCESS",
            "enriched_at": now,
        })

        emit(**fields)
        log_debug(f"Enriched {indicator}: score={score}, cats={true_cats}, remaining_credit={remaining}")

    except Exception as e:
        safe = _scrub(e)
        log_debug(f"EXCEPTION: {safe}")
        emit(indicator="", result="ERROR", message=safe, time=str(int(time.time())))


if __name__ == '__main__':
    main()
