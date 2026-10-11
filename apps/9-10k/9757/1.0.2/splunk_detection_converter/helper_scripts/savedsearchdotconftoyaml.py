#!/usr/bin/env python3
"""Convert a savedsearches.conf export to YAML files. Python 3.9+, no dependencies.

    python3 savedsearchdotconftoyaml.py savedsearches.conf --out converted
    python3 savedsearchdotconftoyaml.py savedsearches.conf --out converted --placeholders

Standalone helper: nothing in the Splunk app imports or runs this file.
The default output follows the original migration's flat fields, including cron
and notable settings. Adapt build_detection() for your repository's schema.
Stock contentctl needs deployment scheduling, or patches to read these flat fields.
"""
import argparse
import hashlib
import json
import re
import sys
import uuid
from datetime import date
from pathlib import Path

# Settings to adapt before running. CLI flags override the corresponding defaults.
AUTHOR = ""                         # Your name/team, used in generated YAML.
STORY_NAME = "Migrated Content"     # Must exist in your content repository.
ASSET_TYPE = "Endpoint"
STATUS = "experimental"
PRESERVE_ENABLED_STATE = False       # Set True to copy the source disabled flag.
STRIP_NAME_DECORATION = False        # Remove e.g. 'Endpoint - ' and ' - Rule'.
SKIP_LIST = []                       # Exact source/output names, case-insensitive.
CREATE_PLACEHOLDERS = False          # Empty lookup CSVs + lookup/macro YAML stubs.
TUNING_NAME_RE = r"(?i)(?:^|[-_])tuning(?:$|[-_])"  # Tuning is a lookup, not a filter macro.
SEARCH_SUFFIX = ""                  # Optional SPL to append; nothing added by default.
CONTINUATION = "\\"                 # Set '/' only for old exports using that marker.
EXTRA_FIELDS = {}                    # e.g. {'schedule_window': 'schedule_window'}.
TODAY = date.today().isoformat()


def customise_detection(detection, stanza):
    """Last mapping hook. Change/remove fields or add your repository's metadata.

    Example: detection['cron_schedule'] = stanza.get('cron_schedule', '*/5 * * * *')
    For stock contentctl, map scheduling/notable fields into a deployment instead.
    """
    pass


def clean_name(name):
    name = name.strip()
    if STRIP_NAME_DECORATION:
        name = re.sub(r"(?i)^(threat|audit|endpoint|network|identity|access)\s*-\s*", "", name)
        name = re.sub(r"(?i)\s*-\s*rule$", "", name)
    return name


def build_search(search):
    search = norm(search).strip()
    return search + ("\n" + SEARCH_SUFFIX.strip() if SEARCH_SUFFIX.strip() else "")


def safe_json_list(raw):
    if not raw:
        return []
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("Expected a JSON array: " + str(raw)[:80])
    return value


def norm(s):
    """tidy text up - unify newline styles and kill weird non-breaking spaces."""
    if s is None:
        return ""
    return str(s).replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")


def as_bool(raw, default=False):
    """splunk writes booleans a dozen ways. treat the obvious truthy ones as true."""
    s = norm(raw).strip().lower()
    return s in ("1", "true", "yes", "y", "on") if s else default


def csv_fields(raw):
    """split  a, b ,c  into a clean list, dropping empties."""
    return [x.strip() for x in norm(raw).split(",") if x.strip()]


def is_placeholder(value):
    """is this just a dummy value someone left lying around? (n/a, none, blank...)"""
    return norm(value).strip().lower() in ("", "n/a", "na", "none", "null")


def seconds_to_duration(value):
    """turn a raw seconds count into 1d / 1h / 30m etc. leaves non-numbers alone."""
    try:
        n = int(str(value).strip())
    except Exception:
        return norm(value).strip()
    if n == 0:
        return "0"
    for size, unit in ((86400, "d"), (3600, "h"), (60, "m")):
        if n % size == 0:
            return f"{n // size}{unit}"
    return f"{n}s"


def norm_offset(raw, default=None):
    """a drilldown time offset can be a $token$, a number of seconds, or already fine."""
    s = norm(raw).strip() or (norm(default).strip() if default is not None else "")
    if not s:
        return None
    if s.startswith("$") and s.endswith("$"):        # leave $info_min_time$ style tokens alone
        return s
    return seconds_to_duration(s) if re.fullmatch(r"\d+", s) else s


class Literal(str):
    """marker type. any string wrapped in this gets written as a |- block scalar."""


def _scalar(v):
    """render a single leaf value (string / int / bool) as inline yaml."""
    if isinstance(v, bool):                          # NB: bool must be checked before int
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return json.dumps(v, ensure_ascii=True, allow_nan=False)


def _emit_kv(key, v, indent, out):
    pad = "  " * indent
    if isinstance(v, Literal) and any(ord(c) < 32 and c not in '\n\t' for c in v):
        v = str(v)  # JSON escaping makes control characters valid YAML strings.
    if isinstance(v, Literal):
        if not str(v).strip():                       # empty -> plain "", dont bother with a block
            out.append(f'{pad}{key}: ""')
            return
        out.append(f"{pad}{key}: |2-")
        for ln in str(v).split("\n"):
            out.append(f"{pad}  {ln.rstrip()}")       # trailing spaces in text dont matter
    elif isinstance(v, dict):
        out.append(f"{pad}{key}:" if v else f"{pad}{key}: {{}}")
        _emit_map(v, indent + 1, out)
    elif isinstance(v, list):
        if not v:
            out.append(f"{pad}{key}: []")
        else:
            out.append(f"{pad}{key}:")
            _emit_seq(v, indent + 1, out)
    else:
        out.append(f"{pad}{key}: {_scalar(v)}")


def _emit_map(d, indent, out):
    for k, v in d.items():
        _emit_kv(k, v, indent, out)


def _emit_seq(items, indent, out):
    pad = "  " * indent
    for item in items:
        if isinstance(item, dict):
            inner = []
            _emit_map(item, indent + 1, inner)
            if not inner:
                out.append(f"{pad}- {{}}")
                continue
            inner[0] = f"{pad}- " + inner[0][len("  " * (indent + 1)):]
            out.extend(inner)
        elif isinstance(item, Literal):
            out.append(f"{pad}- |-")
            for ln in str(item).split("\n"):
                out.append(f"{pad}    {ln.rstrip()}")
        else:
            out.append(f"{pad}- {_scalar(item)}")


def dump_yaml(data):
    out = []
    _emit_map(data, 0, out)
    return "\n".join(out) + "\n"


def map_risk_type(raw):
    """squash splunks many risk-object types down to the 3 contentctl actually knows."""
    raw = (raw or "").lower().strip()
    if raw in ("user", "src_user", "user_name", "identity", "account"):
        return "user"
    if raw in ("other", "n/a", "na"):
        return "other"
    return "system"


def extract_mitre_ids(raw_annotations):
    """
    pull MITRE technique ids (T1234 or T1234.005) out of the annotations json.
    if we have BOTH a parent and one of its sub-techniques, keep only the sub one.
    """
    try:
        parsed = json.loads(raw_annotations) if raw_annotations else {}
    except Exception:
        return []
    if not isinstance(parsed, dict):
        return []
    raw = parsed.get("mitre_attack", [])
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    ids = []
    for item in raw:
        tid = norm(item).strip()
        if re.fullmatch(r"T\d{4}(?:\.\d{3})?", tid) and tid not in ids:
            ids.append(tid)
    return [t for t in ids if "." in t or not any(o.startswith(t + ".") for o in ids)]


def extract_next_steps(stanza):
    """
    analyst guidance from the notable. in the conf its wrapped json like
    {"version":1,"data":"#WorkBook#\\nUse the ... workbook"} - we want JUST the
    inner data string, because the contentctl template re-wraps it in version/data
    on the way back out. really old configs sometimes store plain text instead -
    those pass through as-is.
    """
    raw = norm(stanza.get("action.notable.param.next_steps", "")).strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "data" in parsed:
            inner = norm(parsed["data"]).strip()
            return inner or None
    except Exception:
        pass
    return raw          # not json (or no data key) - take it literally


def build_rba(stanza):
    """
    risk-based-alerting config, faithful to source. returns (rba, primary) or
    (None, None) when theres nothing real to keep.
    """
    if not as_bool(stanza.get("action.risk", "0")):
        return None, None

    raw_msg = norm(stanza.get("action.risk.param._risk_message", "")).strip()

    objects = []
    threat_objects = []
    for item in safe_json_list(stanza.get("action.risk.param._risk", "")):
        if not isinstance(item, dict):
            continue
        if "threat_object_field" in item:
            tfield = norm(item.get("threat_object_field", "")).strip()
            ttype = norm(item.get("threat_object_type", "")).strip()
            if tfield and not is_placeholder(tfield):
                threat_objects.append({"field": tfield, "type": ttype or "other"})
            continue
        fieldname = norm(item.get("risk_object_field", "N/A")).strip()
        if is_placeholder(fieldname):                # drop junk n/a / blank fields
            continue
        try:
            score = int(str(item["risk_score"]))
        except (KeyError, TypeError, ValueError):
            raise ValueError("risk_score must be an integer; refusing to replace it with 0")
        objects.append({
            "field": fieldname,
            "type": map_risk_type(item.get("risk_object_type", "system")),
            "score": score,
        })
    if not objects and not threat_objects:
        return None, None

    primary = objects[0]["field"] if objects else threat_objects[0]["field"]
    rba = {"message": raw_msg, "risk_objects": objects, "threat_objects": threat_objects}
    return rba, primary


def build_dashboards(stanza):
    """custom drilldown dashboards, if any were configured."""
    out = []
    for item in safe_json_list(stanza.get("action.notable.param.drilldown_dashboards", "")):
        if isinstance(item, str):
            item = {"name": item}
        if not isinstance(item, dict):
            continue
        out.append({
            k: (json.dumps(v) if isinstance(v, list) and v else v)
            for k, v in item.items()
        })
    return out


def build_drilldowns(stanza):
    """only the original drilldowns from the source - no stock placeholder ones."""
    searches = []
    for dd in safe_json_list(stanza.get("action.notable.param.drilldown_searches", "")):
        if not isinstance(dd, dict):
            continue
        sval = norm(dd.get("search", ""))
        
        searches.append({
            "name": dd.get("name", "Drilldown"),
            "search": Literal(sval) if "\n" in sval else sval,
            "earliest_offset": norm_offset(dd.get("earliest_offset", ""), "$info_min_time$"),
            "latest_offset": norm_offset(dd.get("latest_offset", ""), "$info_max_time$"),
        })
    return searches


def build_tags(stanza, security_domain, mitre_ids):
    """the tags block - story, asset type, mitre ids, products, throttling."""
    tags = {"analytic_story": [STORY_NAME], "asset_type": ASSET_TYPE}
    if mitre_ids:
        tags["mitre_attack_id"] = mitre_ids
    tags["product"] = ["Splunk Enterprise", "Splunk Enterprise Security", "Splunk Cloud"]
    tags["security_domain"] = security_domain
    period = norm(stanza.get("alert.suppress.period", "")).strip()
    fields = csv_fields(stanza.get("alert.suppress.fields", ""))
    if as_bool(stanza.get("alert.suppress", "0")) and period and fields:
        tags["throttling"] = {"period": period, "fields": fields}
    return tags


def build_detection(raw_name, stanza):
    """
    the heart of it: one parsed stanza -> the dict we'll dump as a detection yaml.
    returns (name, security_domain, det).
    """
    security_domain = norm(
        stanza.get("action.notable.param.security_domain", "endpoint")
    ).strip().lower() or "endpoint"
    name = clean_name(raw_name)
    search = build_search(stanza.get("search", ""))

    rba, primary = build_rba(stanza)

    orig_desc = norm(stanza.get("description", "")).strip()

    notable_enabled = as_bool(stanza.get("action.notable", "0"))

    if notable_enabled and rba:
        det_type = "TTP"
    elif notable_enabled:
        det_type = "Correlation"
    elif rba:
        det_type = "Anomaly"
    else:
        det_type = "Hunting"

    det = {
        "name": name,
        "enabled_by_default": (not as_bool(stanza.get("disabled", "1"))) if PRESERVE_ENABLED_STATE else False,
        "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"detection:{name}")),
        "version": 1,
        "date": TODAY,
        "author": AUTHOR,
        "status": STATUS,
        "type": det_type,
    }

    if notable_enabled:
        det["rule_title"] = norm(stanza.get("action.notable.param.rule_title", "")).strip() or name
        det["rule_description"] = Literal(
            norm(stanza.get("action.notable.param.rule_description", "")).strip() or orig_desc
        )
        severity = norm(stanza.get("action.notable.param.severity", "")).strip().lower()
        if severity:
            det["rule_severity"] = severity

    det["description"] = Literal(orig_desc)
    det["search"] = Literal(search)

    if rba:
        det["rba"] = rba

    dashboards = build_dashboards(stanza)
    if dashboards:
        det["drilldown_dashboards"] = dashboards
    drilldowns = build_drilldowns(stanza)
    if drilldowns:
        det["drilldown_searches"] = drilldowns

    det["cron_schedule"] = norm(stanza.get("cron_schedule", "")).strip()
    earliest = norm(stanza.get("dispatch.earliest_time", "")).strip()
    latest = norm(stanza.get("dispatch.latest_time", "")).strip()
    if earliest:
        det["earliest_time"] = earliest
    if latest:
        det["latest_time"] = latest
    index_earliest = norm(stanza.get("dispatch.index_earliest", "")).strip()
    index_latest = norm(stanza.get("dispatch.index_latest", "")).strip()
    if index_earliest:
        det["index_earliest"] = index_earliest
    if index_latest:
        det["index_latest"] = index_latest
    if norm(stanza.get("realtime_schedule", "")).strip():
        det["realtime_schedule"] = as_bool(stanza.get("realtime_schedule", "0"))
    if norm(stanza.get("enableSched", "")).strip():
        det["enableSched"] = as_bool(stanza.get("enableSched", "0"))
    if norm(stanza.get("allow_skew", "")).strip():
        det["allow_skew"] = norm(stanza.get("allow_skew", "")).strip()

    det["email"] = as_bool(stanza.get("action.email", "0"))
    subject = norm(stanza.get("action.email.subject.alert", "")).strip()
    to = norm(stanza.get("action.email.to", "")).strip()
    message = norm(stanza.get("action.email.message.alert", "")).strip()
    if subject:
        det["subject"] = Literal(subject)
    if to:
        det["to"] = to
    if message:
        det["message"] = Literal(message)
    if norm(stanza.get("action.email.sendresults", "")).strip():
        det["sendresults"] = as_bool(stanza.get("action.email.sendresults", "0"))
    if norm(stanza.get("action.email.sendcsv", "")).strip():
        det["sendcsv"] = as_bool(stanza.get("action.email.sendcsv", "0"))

    mitre_ids = extract_mitre_ids(stanza.get("action.correlationsearch.annotations", ""))
    det["tags"] = build_tags(stanza, security_domain, mitre_ids)

    next_steps = extract_next_steps(stanza)
    if next_steps:
        det["next_steps"] = Literal(next_steps)

    for output_key, source_key in EXTRA_FIELDS.items():
        if source_key in stanza:
            det[output_key] = stanza[source_key]
    customise_detection(det, stanza)
    return name, security_domain, det

# Conf parsing is deliberately separate from field mapping and SPL scanning.
KEY_RE = re.compile(r"^\s*([A-Za-z0-9_.:-]+)\s*=\s*(.*)$")
STANZA_RE = re.compile(r"^\[([^\]]+)\]\s*$")


def parse_conf(path, continuation=CONTINUATION):
    """Read a conf export, including defaults and backslash continuations.

    Also accept indented/pipe-leading SPL from pasted exports. A forward slash
    is not a continuation by default: that would damage URLs and regex strings.
    Duplicate stanzas are rejected; merge layered configs in Splunk before export.
    """
    text = Path(path).read_text(encoding="utf-8-sig")
    records, seen, stanza, name, key, continued = [], set(), {}, None, None, False
    for number, line in enumerate(text.splitlines(), 1):
        line = line.rstrip()
        if not line.strip() or line.lstrip().startswith(("#", ";")):
            continue
        header = STANZA_RE.fullmatch(line)
        # In an explicitly continued value, [search ...] is a subsearch, not a stanza.
        if header and not continued and not header[1].lstrip().startswith("|"):
            if name is not None:
                records.append((name, stanza))
            name = header[1]
            if name.casefold() in seen:
                raise ValueError(f"Line {number}: duplicate stanza [{name}]")
            seen.add(name.casefold())
            stanza, key = {}, None
            continue
        if name is None:
            # Splunk also allows default key/value pairs before any stanza.
            name = "default"
            seen.add(name)
        setting = KEY_RE.fullmatch(line)
        if continued:
            value = line
        elif setting:
            key, value = setting.groups()
            if key in stanza:
                raise ValueError(f"Line {number}: duplicate setting {key} in [{name}]")
            stanza[key] = ""
        elif key and (line[:1].isspace() or (key == "search" and line.startswith(("|", "[", "]")))):
            value = line
        else:
            raise ValueError(f"Line {number}: unrecognised conf line in [{name}]")
        continued = value.endswith(continuation)
        if continued:
            value = value[:-len(continuation)]
        stanza[key] += ("\n" if stanza[key] else "") + value
    if continued:
        raise ValueError("Unfinished continuation at end of file")
    if name is not None:
        records.append((name, stanza))
    defaults = next((s for n, s in records if n.casefold() == "default"), {})
    return [(n, dict(defaults, **s)) for n, s in records if n.casefold() != "default"]


def spl_tokens(search):
    """Tokenise only enough SPL to find literal dependencies, without executing it.

    Skip triple-backtick, /* ... */, and whole-line #/; comments. Quoted strings
    remain single tokens, so embedded '| lookup ...' text cannot become a command.
    Backtick macro calls are separate tokens; their quoted arguments stay intact.
    """
    i = 0
    while i < len(search):
        c = search[i]
        if c.isspace():
            i += 1
            continue
        if search.startswith('```', i) or search.startswith('/*', i):
            marker = '```' if search.startswith('```', i) else '*/'
            start = i + (3 if marker == '```' else 2)
            end = search.find(marker, start)
            if end < 0:
                raise ValueError("Unclosed SPL comment; dependency scan stopped")
            i = end + len(marker)
            continue
        if c in '#;' and not search[search.rfind('\n', 0, i) + 1:i].strip():
            end = search.find('\n', i)
            i = len(search) if end < 0 else end + 1
            continue
        if c in "\"'`":
            quote, start, i = c, i + 1, i + 1
            inner_quote = None
            while i < len(search):
                if search[i] == '\\':
                    i += 2
                elif quote == '`' and inner_quote:
                    if search[i] == inner_quote:
                        inner_quote = None
                    i += 1
                elif quote == '`' and search[i] in "\"'":
                    inner_quote = search[i]
                    i += 1
                elif search[i] == quote:
                    break
                else:
                    i += 1
            if i >= len(search):
                raise ValueError("Unclosed SPL quote/macro; dependency scan stopped")
            yield ('macro' if quote == '`' else 'quoted', search[start:i])
            i += 1
        elif c in '|[]=':
            yield ('symbol', c)
            i += 1
        else:
            start = i
            while i < len(search) and not search[i].isspace() and search[i] not in '|[]=\"\'`':
                # Comments can touch tokens without whitespace.
                if search.startswith('/*', i):
                    break
                i += 1
            yield ('word', search[start:i])


def macro_signature(call):
    match = re.fullmatch(r"\s*([A-Za-z_][\w.-]*)(?:\((.*)\))?\s*", call, re.S)
    if not match or match[1].lower() == 'comment':
        return None
    arguments = match[2]
    if arguments is None or not arguments.strip():
        return match[1], 0
    depth, count, quote, escaped = 0, 1, None, False
    for c in arguments:
        if escaped:
            escaped = False
        elif c == '\\':
            escaped = True
        elif quote:
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
        elif c in '([':
            depth += 1
        elif c in ')]':
            depth -= 1
        elif c == ',' and depth == 0:
            count += 1
        if depth < 0:
            raise ValueError("Unbalanced macro arguments: " + call)
    if quote or depth or escaped:
        raise ValueError("Unbalanced macro arguments: " + call)
    return match[1], count


def dependencies(search):
    tokens = list(spl_tokens(search))
    macros, lookups, unresolved = set(), set(), set()
    command_start = True
    for i, (kind, value) in enumerate(tokens):
        if kind == 'macro':
            signature = macro_signature(value)
            if signature:
                macros.add(signature)
            elif not re.match(r'\s*comment\s*\(', value, re.I):
                unresolved.add('macro: ' + value)
            # comment(...) is removed by Splunk and does not consume command position.
            if signature:
                command_start = False
            continue
        if kind == 'symbol' and value in '|[':
            command_start = True
            continue
        if command_start and kind == 'word' and value.lower() in ('lookup', 'inputlookup', 'outputlookup'):
            j = i + 1
            while j + 2 < len(tokens) and tokens[j][0] == 'word' and tokens[j+1] == ('symbol', '='):
                j += 3  # local=true, append=true, max=..., etc.
            if j < len(tokens) and tokens[j][0] in ('word', 'quoted'):
                target = tokens[j][1]
                if re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_. -]*', target):
                    lookups.add(target)
                else:
                    unresolved.add('lookup: ' + target)
            else:
                unresolved.add('lookup target could not be resolved')
        command_start = False
    return macros, lookups, unresolved


def file_stem(name):
    """Stable, portable filenames; the YAML name still keeps the actual source name.

    The suffix avoids collisions after sanitising, truncation or case folding.
    Change this if your repository imposes its own filename convention.
    """
    slug = re.sub(r'[^A-Za-z0-9_-]+', '_', name).strip('_-')[:90] or 'content'
    if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])', slug):
        slug = '_' + slug
    return slug + '__' + hashlib.sha256(name.encode('utf-8')).hexdigest()[:12]


def placeholder_files(macros, lookups):
    """Blank definitions/data only. Names and argument counts come from active SPL.

    Real macro arg names, definitions, lookup columns and KV Store/transform
    details cannot be recovered from savedsearches.conf. Fill them in yourself.
    Tuning lookups use the same YAML/CSV pair as other lookups, under lookups/.
    """
    files = {}
    for name, count in sorted(macros):
        key = name + (f'({count})' if count else '')
        files['macros/' + file_stem(key) + '.yml'] = dump_yaml({
            'name': name, 'definition': '',
            'description': 'Placeholder. Fill in the macro definition and argument names.',
            'arguments': [f'arg{i+1}' for i in range(count)]})
    csv_names = set()
    for name in sorted(lookups):
        stem = file_stem(name)
        # A literal inputlookup foo.csv still needs a file actually called foo.csv.
        csv_name = name if name.lower().endswith('.csv') else stem + '.csv'
        if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\..*)?', csv_name):
            raise ValueError('Lookup uses a reserved filename; adapt its mapping: ' + name)
        if csv_name.casefold() in csv_names:
            raise ValueError('Lookup filenames differ only by case; resolve before exporting: ' + name)
        csv_names.add(csv_name.casefold())
        tuning = bool(re.search(TUNING_NAME_RE, re.sub(r'(?i)\.csv$', '', name)))
        files['lookups/' + stem + '.yml'] = dump_yaml({
            'name': name, 'id': str(uuid.uuid5(uuid.NAMESPACE_URL, 'lookup:' + name)),
            'version': 1, 'date': TODAY, 'author': AUTHOR,
            'description': ('Tuning lookup' if tuning else 'Lookup') + ' placeholder. Add the real data and lookup settings.',
            'lookup_type': 'csv', 'file_path': csv_name})
        files['lookups/' + csv_name] = ''
    return files


def write_outputs(out, files):
    """Write into a new/empty directory and never overwrite an existing file."""
    if out.exists() and (out.is_symlink() or not out.is_dir() or any(out.iterdir())):
        raise ValueError('Output must be a new or empty directory: ' + str(out))
    for relative, content in files.items():
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(content)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('infile', type=Path)
    parser.add_argument('--out', type=Path, default=Path('converted'))
    parser.add_argument('--placeholders', action=argparse.BooleanOptionalAction, default=CREATE_PLACEHOLDERS,
                        help='Create blank macro and lookup/tuning files from active SPL only')
    parser.add_argument('--cont', choices=['\\', '/'], default=CONTINUATION)
    args = parser.parse_args(argv)
    try:
        stanzas = parse_conf(args.infile, args.cont)
        files, errors, skipped = {}, [], 0
        all_macros, all_lookups, unresolved = set(), set(), set()
        skip = {name.casefold() for name in SKIP_LIST}
        for raw_name, stanza in stanzas:
            if not stanza.get('search', '').strip() or raw_name.casefold() in skip or clean_name(raw_name).casefold() in skip:
                skipped += 1
                continue
            try:
                name, domain, detection = build_detection(raw_name, stanza)
                relative = 'detections/' + file_stem(raw_name) + '.yml'
                files[relative] = dump_yaml(detection)
                if args.placeholders:
                    macros, lookups, pending = dependencies(stanza['search'])
                    all_macros.update(macros)
                    all_lookups.update(lookups)
                    unresolved.update(raw_name + ': ' + item for item in pending)
            except (ValueError, TypeError, KeyError) as exc:
                errors.append(raw_name + ': ' + str(exc))
        # Do not leave an apparently complete migration after dropping malformed stanzas.
        if errors:
            raise ValueError('\n'.join(errors))
        if args.placeholders:
            files.update(placeholder_files(all_macros, all_lookups))
        write_outputs(args.out, files)
        print(f'{len(stanzas)-skipped} detections written, {skipped} stanzas skipped. Output: {args.out}')
        for item in sorted(unresolved):
            print('Unresolved dependency: ' + item, file=sys.stderr)
        return 2 if unresolved else 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
