#!/usr/bin/env python3
"""
parse_arf.py — Layer 1: CIS-CAT ARF XML Parser
Compliance Posture for Splunk | GIC Engineering Consultants

Standalone, Splunk-independent module. Zero Splunk imports.
Importable from any Python environment. Portable to any platform or SIEM.

Input:  CIS-CAT Pro v4 ARF XML file path or XML string
Output: List of normalized JSON-serializable dicts (one per rule-result)
        plus one summary dict for the assessment-level fields

Usage (standalone):
    python3 parse_arf.py <path_to_arf.xml>

Usage (from upload_handler.py):
    from parse_arf import parse_arf_file
    events = parse_arf_file(file_path, upload_time, upload_batch_id)
"""

import xml.etree.ElementTree as ET
import json
import sys
import os
import re
from datetime import datetime, timezone


# ── Namespace map ────────────────────────────────────────────────────────────
NS = {
    'arf':   'http://scap.nist.gov/schema/asset-reporting-format/1.1',
    'ai':    'http://scap.nist.gov/schema/asset-identification/1.1',
    'xccdf': 'http://checklists.nist.gov/xccdf/1.2',
    'xsi':   'http://www.w3.org/2001/XMLSchema-instance',
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _text(element, path, ns=NS, default=''):
    """Safely extract text from an element found by xpath."""
    found = element.find(path, ns)
    if found is not None and found.text:
        return found.text.strip()
    return default


def _attr(element, attr, default=''):
    """Safely extract an attribute value from an element."""
    val = element.get(attr)
    return val.strip() if val else default


def _extract_profile_label(idref):
    """
    Convert profile idref to human-readable label.

    Examples:
      xccdf_org.cisecurity.benchmarks_profile_Level_1_-_Member_Server
        -> Level 1 - Member Server
      xccdf_org.cisecurity.benchmarks_profile_Level_2_-_Server
        -> Level 2 - Server
      xccdf_org.cisecurity.benchmarks_profile_Level_1
        -> Level 1
    """
    marker = '_profile_'
    idx = idref.find(marker)
    if idx == -1:
        return idref
    raw = idref[idx + len(marker):]
    return raw.replace('_', ' ').strip()


def _extract_rule_id(idref):
    """
    Extract the short rule identifier from the full idref.

    Input:  xccdf_org.cisecurity.benchmarks_rule_1.1.1_Ensure_Enforce_...
    Output: 1.1.1

    The rule number is the segment immediately after '_rule_' up to the
    first underscore that follows a digit (i.e., where the description starts).
    """
    marker = '_rule_'
    idx = idref.find(marker)
    if idx == -1:
        return idref
    remainder = idref[idx + len(marker):]
    # Rule number: digits and dots until the first underscore after the number
    match = re.match(r'^([\d.]+)', remainder)
    if match:
        return match.group(1)
    return remainder


def _extract_rule_title(idref):
    """
    Extract human-readable rule title from the full idref.

    Input:  xccdf_org.cisecurity.benchmarks_rule_1.1.1_Ensure_Enforce_password_history_...
    Output: Ensure Enforce password history ...

    Everything after the rule number, underscores replaced with spaces.
    """
    marker = '_rule_'
    idx = idref.find(marker)
    if idx == -1:
        return idref
    remainder = idref[idx + len(marker):]
    # Strip leading rule number (digits and dots)
    title_part = re.sub(r'^[\d.]+_', '', remainder)
    return title_part.replace('_', ' ').strip()


def _extract_benchmark_section(rule_id):
    """
    Derive benchmark section from rule_id for Remediation Report grouping.

    Input:  1.1.3
    Output: 1  (top-level section number)

    Input:  17.5.1
    Output: 17
    """
    parts = rule_id.split('.')
    if parts:
        return parts[0]
    return rule_id


def _safe_float(value, default=0.0):
    """Safely convert a value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _strip_large_sections(xml_string):
    """
    Pre-process ARF XML to remove large sections the parser does not read.

    CIS-CAT ARF files embed full OVAL definitions, OVAL results, system
    characteristics, and the complete xccdf:Benchmark block.  These can push
    real-world files to 13 MB+, triggering lxml's default 10 MB text-node
    limit on Splunk Cloud Victoria (xmlSAX2Characters: huge text node).

    The parser only needs:
      - xccdf:TestResult   (inside arf:reports)
      - arf:assets          (for fallback hostname/IP)

    Stripping the unused blocks reduces a typical 13 MB file to ~1.3 MB
    with zero data loss.  Customer-validated by Rob Bowden at Hydro Tasmania.
    """
    # Patterns for large blocks to remove (namespace-aware, greedy across lines)
    # Each pattern targets an element the parser never reads.
    patterns = [
        # Full benchmark definition (largest block in most ARF files)
        r'<xccdf:Benchmark\b[^>]*>.*?</xccdf:Benchmark>',
        # OVAL definitions
        r'<oval_definitions\b[^>]*>.*?</oval_definitions>',
        r'<[^:>]*:oval_definitions\b[^>]*>.*?</[^:>]*:oval_definitions>',
        # OVAL results
        r'<oval_results\b[^>]*>.*?</oval_results>',
        r'<[^:>]*:oval_results\b[^>]*>.*?</[^:>]*:oval_results>',
        # OVAL system characteristics
        r'<oval_system_characteristics\b[^>]*>.*?</oval_system_characteristics>',
        r'<[^:>]*:oval_system_characteristics\b[^>]*>.*?</[^:>]*:oval_system_characteristics>',
    ]
    for pattern in patterns:
        xml_string = re.sub(pattern, '', xml_string, flags=re.DOTALL)

    return xml_string


# ── Core parser ──────────────────────────────────────────────────────────────

def parse_arf_string(xml_string, upload_time=None, upload_batch_id=''):
    """
    Parse a CIS-CAT ARF XML string.

    Args:
        xml_string (str):        Raw ARF XML content.
        upload_time (str):       ISO timestamp of upload (defaults to now).
        upload_batch_id (str):   Batch identifier from upload handler.

    Returns:
        list[dict]: One dict per rule-result event, Splunk-ingestible JSON.
                    All events share the same assessment-level fields.
    """
    if upload_time is None:
        upload_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')

    # Strip large XML sections the parser does not need (CIS-005).
    # Prevents lxml XMLSyntaxError on Splunk Cloud Victoria for files >10 MB.
    xml_string = _strip_large_sections(xml_string)

    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        raise ValueError(f"ARF XML parse error: {e}")

    # ── Locate TestResult ────────────────────────────────────────────────────
    test_result = root.find('.//xccdf:TestResult', NS)
    if test_result is None:
        raise ValueError("No xccdf:TestResult element found in ARF XML.")

    # ── Assessment-level fields ──────────────────────────────────────────────
    assessment_time  = _attr(test_result, 'start-time')
    benchmark_version = _attr(test_result, 'version')

    benchmark_title = _text(test_result, 'xccdf:title')

    # Hostname: prefer xccdf:target, fall back to ai:hostname in assets block
    asset_hostname = _text(test_result, 'xccdf:target')
    if not asset_hostname:
        asset_hostname = _text(root, './/ai:hostname', default='')

    # IP address: xccdf:target-address (may be absent — edge case FINSW01)
    asset_ip = _text(test_result, 'xccdf:target-address', default='')

    # Target facts: fqdn, os_name, os_version (any may be absent)
    asset_fqdn  = ''
    os_name     = ''
    os_version  = ''
    for fact in test_result.findall('xccdf:target-facts/xccdf:fact', NS):
        name = _attr(fact, 'name')
        val  = fact.text.strip() if fact.text else ''
        if 'fqdn' in name:
            asset_fqdn = val
        elif 'os_name' in name:
            os_name = val
        elif 'os_version' in name:
            os_version = val

    # Profile: readable label extracted from idref
    profile_elem = test_result.find('xccdf:profile', NS)
    profile = ''
    if profile_elem is not None:
        profile = _extract_profile_label(_attr(profile_elem, 'idref'))

    # Score fields
    score_elem = test_result.find('xccdf:score', NS)
    compliance_score = 0.0
    score_max        = 100.0
    score_value      = 0.0
    if score_elem is not None:
        compliance_score = _safe_float(score_elem.text)
        score_max        = _safe_float(_attr(score_elem, 'maximum'), 100.0)
        score_value      = compliance_score

    # ── Per-rule events ──────────────────────────────────────────────────────
    events = []

    for rule_result in test_result.findall('xccdf:rule-result', NS):
        idref       = _attr(rule_result, 'idref')
        rule_weight = _safe_float(_attr(rule_result, 'weight', '1.0'))
        severity    = _attr(rule_result, 'severity', default='')  # may be absent
        rule_time   = _attr(rule_result, 'time')

        result_elem = rule_result.find('xccdf:result', NS)
        result = result_elem.text.strip() if (result_elem is not None and result_elem.text) else 'unknown'

        rule_id      = _extract_rule_id(idref)
        rule_title   = _extract_rule_title(idref)
        rule_section = _extract_benchmark_section(rule_id)

        event = {
            # Assessment-level fields (same for every rule in this scan)
            'asset_hostname':     asset_hostname,
            'asset_ip':           asset_ip,
            'asset_fqdn':         asset_fqdn,
            'os_name':            os_name,
            'os_version':         os_version,
            'benchmark_title':    benchmark_title,
            'benchmark_version':  benchmark_version,
            'profile':            profile,
            'assessment_time':    assessment_time,
            'compliance_score':   compliance_score,
            'score_max':          score_max,
            'score_value':        score_value,

            # Rule-level fields
            'rule_id':            rule_id,
            'rule_title':         rule_title,
            'rule_section':       rule_section,
            'result':             result,
            'rule_weight':        rule_weight,
            'severity':           severity,
            'rule_time':          rule_time,

            # Upload tracking fields (injected by upload handler)
            'upload_time':        upload_time,
            'upload_batch_id':    upload_batch_id,

            # Splunk indexing timestamp — always upload_time, never assessment_time.
            # assessment_time reflects when the scan ran (may be past or future-dated).
            # _time must be grounded in the present to avoid MAX_DAYS_HENCE rejection.
            # Trend charts should group by assessment_time, not _time.
            '_time':              upload_time,
        }

        events.append(event)

    if not events:
        raise ValueError("ARF XML contained no rule-result elements.")

    return events


def parse_arf_file(file_path, upload_time=None, upload_batch_id=''):
    """
    Parse a CIS-CAT ARF XML file by path.

    Args:
        file_path (str):         Path to ARF XML file.
        upload_time (str):       ISO timestamp of upload.
        upload_batch_id (str):   Batch identifier.

    Returns:
        list[dict]: Normalized rule-result events.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"ARF XML file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        xml_string = f.read()

    return parse_arf_string(xml_string, upload_time=upload_time,
                            upload_batch_id=upload_batch_id)


# ── Standalone runner ────────────────────────────────────────────────────────

def _print_summary(events):
    """Print a concise summary of parsed events for validation."""
    if not events:
        print("No events parsed.")
        return

    first = events[0]
    print(f"\n{'='*60}")
    print(f"  Host:       {first['asset_hostname']}")
    print(f"  IP:         {first['asset_ip'] or '(not present)'}")
    print(f"  FQDN:       {first['asset_fqdn'] or '(not present)'}")
    print(f"  OS:         {first['os_name']} {first['os_version']}")
    print(f"  Benchmark:  {first['benchmark_title']} v{first['benchmark_version']}")
    print(f"  Profile:    {first['profile']}")
    print(f"  Scan Time:  {first['assessment_time']}")
    print(f"  Score:      {first['compliance_score']}%")
    print(f"  Rules:      {len(events)} total")

    # Result counts
    from collections import Counter
    result_counts = Counter(e['result'] for e in events)
    for result, count in sorted(result_counts.items()):
        print(f"    {result:<20} {count}")

    # Zero-weight rules
    zero_weight = [e for e in events if e['rule_weight'] == 0.0]
    if zero_weight:
        print(f"  Zero-weight rules: {len(zero_weight)}")

    # Missing severity
    no_severity = [e for e in events if not e['severity']]
    if no_severity:
        print(f"  Rules without severity: {len(no_severity)}")

    print(f"{'='*60}\n")

    # Show first 3 events as sample
    print("Sample events (first 3):")
    for e in events[:3]:
        print(f"  [{e['result']:>15}]  {e['rule_id']:<12}  {e['rule_title'][:60]}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 parse_arf.py <arf_xml_file> [--json]")
        sys.exit(1)

    file_path  = sys.argv[1]
    json_output = '--json' in sys.argv

    try:
        events = parse_arf_file(
            file_path,
            upload_time='2026-02-19T08:00:00',
            upload_batch_id='test_batch_001'
        )

        if json_output:
            print(json.dumps(events, indent=2))
        else:
            _print_summary(events)

        print(f"SUCCESS: {len(events)} events parsed from {os.path.basename(file_path)}")
        sys.exit(0)

    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
