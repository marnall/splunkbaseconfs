#!/usr/bin/env python3
"""
STIG Checklist (.ckl / .cklb) Parser for Splunk Ingestion
Marcus House

This script parses DISA STIG Viewer checklist files and outputs
JSON events suitable for Splunk ingestion.

Supported formats:
    - .ckl  (XML-based, STIG Viewer 2.x)
    - .cklb (JSON-based, STIG Viewer 3.x)

Usage:
    python3 parse_ckl.py <checklist_file> [--output json|csv]
    python3 parse_ckl.py /path/to/checklist.ckl --output json
    python3 parse_ckl.py /path/to/checklist.cklb --output json
    python3 parse_ckl.py /path/to/checklist.ckl --output csv

Output can be piped to Splunk via:
    - HTTP Event Collector (HEC)
    - Monitor input on output file
    - Scripted input

Author: Marcus House
Date: February 2026
"""

import xml.etree.ElementTree as ET
import json
import csv
import sys
import os
import re
import argparse
import uuid
from datetime import datetime, timezone


# Maximum size (bytes) for any single XML text node.
# Splunk Cloud Victoria uses lxml which has a 10 MB default limit.
# Set to 5 MB to provide safety margin.
_MAX_TEXT_NODE_BYTES = 5 * 1024 * 1024

# Regex: match text content between > and < that exceeds the limit
_RE_TEXT_NODE = re.compile(r'(>[^<]{%d,}<)' % _MAX_TEXT_NODE_BYTES)


def _preprocess_ckl_xml(filepath):
    """Read a CKL file and truncate any XML text nodes exceeding the safe
    size limit.  Returns the sanitized XML string for ET.fromstring().

    This prevents lxml.etree.XMLSyntaxError ('huge text node') on Splunk
    Cloud Victoria, which uses lxml with a default 10 MB text-node cap.
    Standard CKL files rarely hit this, but production checklists with
    very large FINDING_DETAILS or COMMENTS fields can approach the limit.
    See STIG-014 / CIS-005.
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()

    def _truncate(match):
        full = match.group(0)
        # Keep opening >, trim content, keep closing <
        return full[:_MAX_TEXT_NODE_BYTES] + '... [truncated]<'

    sanitized = _RE_TEXT_NODE.sub(_truncate, raw)
    return sanitized


def parse_asset_info(checklist_root):
    """Extract asset information from the CHECKLIST/ASSET element."""
    asset = {}
    asset_elem = checklist_root.find('ASSET')
    
    if asset_elem is not None:
        # Standard asset fields
        asset_fields = [
            'ROLE', 'ASSET_TYPE', 'HOST_NAME', 'HOST_IP', 'HOST_MAC',
            'HOST_FQDN', 'TARGET_COMMENT', 'TECH_AREA', 'TARGET_KEY',
            'WEB_OR_DATABASE', 'WEB_DB_SITE', 'WEB_DB_INSTANCE'
        ]
        
        for field in asset_fields:
            elem = asset_elem.find(field)
            if elem is not None and elem.text:
                asset[field.lower()] = elem.text.strip()
            else:
                asset[field.lower()] = ""
    
    return asset


def parse_stig_info(istig_elem):
    """Extract STIG metadata from the STIG_INFO element."""
    stig_info = {}
    stig_info_elem = istig_elem.find('STIG_INFO')
    
    if stig_info_elem is not None:
        for si_data in stig_info_elem.findall('SI_DATA'):
            sid_name = si_data.find('SID_NAME')
            sid_data = si_data.find('SID_DATA')
            
            if sid_name is not None and sid_name.text:
                key = sid_name.text.strip().lower()
                value = sid_data.text.strip() if sid_data is not None and sid_data.text else ""
                stig_info[key] = value
    
    return stig_info


def parse_vuln(vuln_elem):
    """Parse a single VULN element and extract all relevant fields."""
    vuln = {}
    
    # Parse STIG_DATA elements (vulnerability metadata)
    for stig_data in vuln_elem.findall('STIG_DATA'):
        vuln_attr = stig_data.find('VULN_ATTRIBUTE')
        attr_data = stig_data.find('ATTRIBUTE_DATA')
        
        if vuln_attr is not None and vuln_attr.text:
            key = vuln_attr.text.strip().lower()
            value = attr_data.text.strip() if attr_data is not None and attr_data.text else ""
            vuln[key] = value
    
    # Parse direct child elements (status, finding details, comments)
    direct_fields = ['STATUS', 'FINDING_DETAILS', 'COMMENTS', 'SEVERITY_OVERRIDE',
                     'SEVERITY_JUSTIFICATION']
    
    for field in direct_fields:
        elem = vuln_elem.find(field)
        if elem is not None and elem.text:
            vuln[field.lower()] = elem.text.strip()
        else:
            vuln[field.lower()] = ""
    
    return vuln


def map_severity_to_category(severity):
    """Map severity string to CAT level."""
    severity_map = {
        'high': 'CAT I',
        'medium': 'CAT II',
        'low': 'CAT III'
    }
    return severity_map.get(severity.lower(), 'Unknown')


def parse_cklb_file(filepath):
    """
    Parse a .cklb file (JSON-based, STIG Viewer 3.x) and return a list
    of vulnerability events with the same schema as .ckl parsing.

    The .cklb format stores the same data as .ckl but in JSON structure:
    {
        "target_data": { "host_name": ..., "ip_address": ..., ... },
        "stigs": [
            {
                "stig_name": ..., "display_name": ..., "stig_id": ...,
                "version": ..., "release_info": ...,
                "rules": [
                    {
                        "group_id": ..., "group_id_src": ...,
                        "severity": ..., "rule_id": ..., "rule_id_src": ...,
                        "rule_version": ..., "title": ...,
                        "vuln_discussion": ..., "check_content": ...,
                        "fix_text": ..., "status": ...,
                        "finding_details": ..., "comments": ...,
                        "severity_override": ..., "severity_justification": ...
                    }, ...
                ]
            }, ...
        ]
    }
    """
    events = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return events
    except FileNotFoundError:
        print(f"File not found: {filepath}", file=sys.stderr)
        return events

    # Generate upload tracking fields
    upload_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    upload_batch_id = str(uuid.uuid4())

    # Extract assessment_time from file modification date
    # This represents when the assessor last saved the checklist, i.e. the scan date
    try:
        file_mtime = os.path.getmtime(filepath)
        assessment_time = datetime.fromtimestamp(file_mtime, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    except OSError:
        assessment_time = upload_time

    # Extract target/asset data
    target = data.get('target_data', {})
    asset_info = {
        'role': target.get('role', ''),
        'asset_type': target.get('asset_type', target.get('computing', '')),
        'host_name': target.get('host_name', ''),
        'host_ip': target.get('ip_address', target.get('host_ip', '')),
        'host_mac': target.get('mac_address', target.get('host_mac', '')),
        'host_fqdn': target.get('fqdn', target.get('host_fqdn', '')),
        'target_comment': target.get('target_comment', target.get('comments', '')),
        'tech_area': target.get('tech_area', ''),
        'target_key': target.get('target_key', ''),
        'web_or_database': target.get('web_or_database', ''),
        'web_db_site': target.get('web_db_site', ''),
        'web_db_instance': target.get('web_db_instance', ''),
    }

    file_info = {
        'source_file': os.path.basename(filepath),
        'source_format': 'cklb',
        'parse_time': upload_time,
        'upload_time': upload_time,
        'upload_batch_id': upload_batch_id,
        'assessment_time': assessment_time,
    }

    # Process each STIG
    for stig in data.get('stigs', []):
        stig_info = {
            'title': stig.get('display_name', stig.get('stig_name', '')),
            'stigid': stig.get('stig_id', ''),
            'version': str(stig.get('version', '')),
            'releaseinfo': stig.get('release_info', ''),
            'filename': stig.get('filename', ''),
            'uuid': stig.get('uuid', ''),
        }

        # Process each rule/vulnerability
        for rule in stig.get('rules', []):
            event = {}
            event['_time'] = upload_time

            # Asset info
            for key, value in asset_info.items():
                event[f'asset_{key}'] = value

            # STIG info
            for key, value in stig_info.items():
                event[f'stig_{key}'] = value

            # Map .cklb rule fields to the same vuln_ schema as .ckl
            # Status mapping: .cklb uses different status strings
            status_raw = rule.get('status', '')
            status_map = {
                'not_a_finding': 'NotAFinding',
                'notafinding': 'NotAFinding',
                'open': 'Open',
                'not_applicable': 'Not_Applicable',
                'not_reviewed': 'Not_Reviewed',
            }
            normalized_status = status_map.get(status_raw.lower(), status_raw)

            event['vuln_vuln_num'] = rule.get('group_id', rule.get('group_id_src', ''))
            event['vuln_severity'] = rule.get('severity', '')
            event['vuln_group_title'] = rule.get('group_id_src', '')
            event['vuln_rule_id'] = rule.get('rule_id_src', rule.get('rule_id', ''))
            event['vuln_rule_ver'] = rule.get('rule_version', '')
            event['vuln_rule_title'] = rule.get('title', '')
            event['vuln_vuln_discuss'] = rule.get('vuln_discussion', '')
            event['vuln_check_content'] = rule.get('check_content', '')
            event['vuln_fix_text'] = rule.get('fix_text', '')
            event['vuln_status'] = normalized_status
            event['vuln_finding_details'] = rule.get('finding_details', '')
            event['vuln_comments'] = rule.get('comments', '')
            event['vuln_severity_override'] = rule.get('severity_override', '')
            event['vuln_severity_justification'] = rule.get('severity_justification', '')

            # Derived fields
            if event['vuln_severity']:
                event['category'] = map_severity_to_category(event['vuln_severity'])

            # File metadata
            event.update(file_info)

            # Sourcetype (same as .ckl for unified dashboards)
            event['sourcetype'] = 'stig:ckl'

            events.append(event)

    return events


def parse_ckl_file(filepath):
    """
    Parse a .ckl file and return a list of vulnerability events.
    
    Each event contains:
    - Asset information (hostname, IP, etc.)
    - STIG information (title, version, release)
    - Vulnerability details (V-number, severity, status, etc.)
    - Upload tracking fields (upload_time, upload_batch_id)
    """
    events = []
    
    try:
        sanitized_xml = _preprocess_ckl_xml(filepath)
        root = ET.fromstring(sanitized_xml)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        return events
    except FileNotFoundError:
        print(f"File not found: {filepath}", file=sys.stderr)
        return events
    
    # Generate upload tracking fields
    upload_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    upload_batch_id = str(uuid.uuid4())
    
    # Extract assessment_time from file modification date
    # This represents when the assessor last saved the checklist, i.e. the scan date
    try:
        file_mtime = os.path.getmtime(filepath)
        assessment_time = datetime.fromtimestamp(file_mtime, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    except OSError:
        assessment_time = upload_time
    
    # Extract asset information (common to all vulns)
    asset_info = parse_asset_info(root)
    
    # Get file metadata
    file_info = {
        'source_file': os.path.basename(filepath),
        'source_format': 'ckl',
        'parse_time': upload_time,
        'upload_time': upload_time,
        'upload_batch_id': upload_batch_id,
        'assessment_time': assessment_time,
    }
    
    # Process each STIG in the checklist
    stigs_elem = root.find('STIGS')
    if stigs_elem is None:
        print("No STIGS element found in checklist", file=sys.stderr)
        return events
    
    for istig in stigs_elem.findall('iSTIG'):
        # Get STIG-level info
        stig_info = parse_stig_info(istig)
        
        # Process each vulnerability
        for vuln_elem in istig.findall('VULN'):
            vuln = parse_vuln(vuln_elem)
            
            # Build the complete event
            event = {}
            
            # Add timestamp (use current time for ingestion tracking)
            event['_time'] = upload_time
            
            # Add asset info with prefix
            for key, value in asset_info.items():
                event[f'asset_{key}'] = value
            
            # Add STIG info with prefix
            for key, value in stig_info.items():
                event[f'stig_{key}'] = value
            
            # Add vulnerability info
            for key, value in vuln.items():
                event[f'vuln_{key}'] = value
            
            # Add derived fields
            if 'severity' in vuln:
                event['category'] = map_severity_to_category(vuln['severity'])
            
            # Add file metadata
            event.update(file_info)
            
            # Add sourcetype for Splunk
            event['sourcetype'] = 'stig:ckl'
            
            events.append(event)
    
    return events


def parse_checklist_file(filepath):
    """
    Detect format by file extension and route to the appropriate parser.
    
    Returns the same event schema regardless of input format.
    """
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext == '.cklb':
        return parse_cklb_file(filepath)
    elif ext == '.ckl':
        return parse_ckl_file(filepath)
    else:
        # Try XML first, fall back to JSON
        try:
            ET.fromstring(_preprocess_ckl_xml(filepath))
            return parse_ckl_file(filepath)
        except ET.ParseError:
            try:
                with open(filepath, 'r') as f:
                    json.load(f)
                return parse_cklb_file(filepath)
            except (json.JSONDecodeError, Exception):
                print(f"Unrecognized file format: {filepath}", file=sys.stderr)
                return []


def output_json(events, output_file=None):
    """Output events as JSON (one event per line for Splunk)."""
    output = output_file if output_file else sys.stdout
    
    for event in events:
        if output_file:
            with open(output_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
        else:
            print(json.dumps(event))


def output_csv(events, output_file=None):
    """Output events as CSV."""
    if not events:
        return
    
    # Get all unique keys across all events
    all_keys = set()
    for event in events:
        all_keys.update(event.keys())
    
    # Sort keys for consistent output
    fieldnames = sorted(all_keys)
    
    if output_file:
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(events)
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)


def print_summary(events):
    """Print a summary of parsed vulnerabilities."""
    if not events:
        print("No vulnerabilities parsed.", file=sys.stderr)
        return
    
    # Count by status
    status_counts = {}
    category_counts = {}
    
    for event in events:
        status = event.get('vuln_status', 'Unknown')
        category = event.get('category', 'Unknown')
        
        status_counts[status] = status_counts.get(status, 0) + 1
        category_counts[category] = category_counts.get(category, 0) + 1
    
    print("\n=== STIG Checklist Summary ===", file=sys.stderr)
    print(f"Total Vulnerabilities: {len(events)}", file=sys.stderr)
    
    print("\nBy Status:", file=sys.stderr)
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}", file=sys.stderr)
    
    print("\nBy Category:", file=sys.stderr)
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}", file=sys.stderr)
    
    # Get asset and STIG info from first event
    if events:
        first = events[0]
        print(f"\nAsset: {first.get('asset_host_name', 'Unknown')}", file=sys.stderr)
        print(f"STIG: {first.get('stig_title', 'Unknown')}", file=sys.stderr)
        print(f"Version: {first.get('stig_version', 'Unknown')}", file=sys.stderr)


def generate_sample_ckl():
    """Generate a sample .ckl file for testing."""
    sample_ckl = '''<?xml version="1.0" encoding="UTF-8"?>
<CHECKLIST>
  <ASSET>
    <ROLE>Member Server</ROLE>
    <ASSET_TYPE>Computing</ASSET_TYPE>
    <HOST_NAME>SPLUNK-IDX01</HOST_NAME>
    <HOST_IP>198.51.100.93</HOST_IP>
    <HOST_MAC>00:50:56:AB:CD:EF</HOST_MAC>
    <HOST_FQDN>splunk-idx01.example.com</HOST_FQDN>
    <TARGET_COMMENT>Splunk Indexer Node 1</TARGET_COMMENT>
    <TECH_AREA></TECH_AREA>
    <TARGET_KEY>12345</TARGET_KEY>
    <WEB_OR_DATABASE>false</WEB_OR_DATABASE>
    <WEB_DB_SITE></WEB_DB_SITE>
    <WEB_DB_INSTANCE></WEB_DB_INSTANCE>
  </ASSET>
  <STIGS>
    <iSTIG>
      <STIG_INFO>
        <SI_DATA>
          <SID_NAME>version</SID_NAME>
          <SID_DATA>2</SID_DATA>
        </SI_DATA>
        <SI_DATA>
          <SID_NAME>releaseinfo</SID_NAME>
          <SID_DATA>Release: 1 Benchmark Date: 15 Jan 2026</SID_DATA>
        </SI_DATA>
        <SI_DATA>
          <SID_NAME>title</SID_NAME>
          <SID_DATA>Red Hat Enterprise Linux 8 STIG</SID_DATA>
        </SI_DATA>
        <SI_DATA>
          <SID_NAME>stigid</SID_NAME>
          <SID_DATA>RHEL_8_STIG</SID_DATA>
        </SI_DATA>
      </STIG_INFO>
      <VULN>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Vuln_Num</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>V-230221</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Severity</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>high</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Group_Title</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>SRG-OS-000480-GPOS-00227</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Rule_ID</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>SV-230221r858734_rule</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Rule_Ver</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>RHEL-08-010000</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Rule_Title</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>RHEL 8 must be a vendor-supported release.</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Vuln_Discuss</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>An operating system release is considered "supported" if the vendor continues to provide security patches for the product.</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Check_Content</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>Verify the version of the operating system is vendor supported. Check the version of the operating system with the following command: $ sudo cat /etc/redhat-release</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Fix_Text</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>Upgrade to a supported version of RHEL 8.</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STATUS>NotAFinding</STATUS>
        <FINDING_DETAILS>Red Hat Enterprise Linux release 8.9 (Ootpa) - Supported version verified.</FINDING_DETAILS>
        <COMMENTS>Reviewed 2026-02-02 by mhouse</COMMENTS>
        <SEVERITY_OVERRIDE></SEVERITY_OVERRIDE>
        <SEVERITY_JUSTIFICATION></SEVERITY_JUSTIFICATION>
      </VULN>
      <VULN>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Vuln_Num</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>V-230222</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Severity</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>medium</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Group_Title</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>SRG-OS-000480-GPOS-00228</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Rule_ID</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>SV-230222r627750_rule</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Rule_Ver</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>RHEL-08-010010</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Rule_Title</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>RHEL 8 vendor packaged system security patches and updates must be installed and up to date.</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Vuln_Discuss</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>Timely patching is critical for maintaining the operational availability, confidentiality, and integrity of information technology (IT) systems.</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Check_Content</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>Verify the operating system security patches and updates are installed and up to date. Updates are required to be applied with a frequency determined by the site or Program Management Office (PMO).</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Fix_Text</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>Install the operating system patches or updated packages available from Red Hat within 30 days or sooner as local policy dictates.</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STATUS>Open</STATUS>
        <FINDING_DETAILS>Last patched 2025-12-15. Updates pending approval.</FINDING_DETAILS>
        <COMMENTS>POA&amp;M item #2026-001 - patches scheduled for next maintenance window</COMMENTS>
        <SEVERITY_OVERRIDE></SEVERITY_OVERRIDE>
        <SEVERITY_JUSTIFICATION></SEVERITY_JUSTIFICATION>
      </VULN>
      <VULN>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Vuln_Num</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>V-230223</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Severity</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>low</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Group_Title</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>SRG-OS-000023-GPOS-00006</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Rule_ID</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>SV-230223r743916_rule</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Rule_Ver</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>RHEL-08-010020</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Rule_Title</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>RHEL 8 must display the Standard Mandatory DoD Notice and Consent Banner before granting local or remote access to the system via a ssh logon.</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Vuln_Discuss</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>Display of a standardized and approved use notification before granting access to the operating system ensures privacy and security notification verbiage used is consistent with applicable federal laws.</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Check_Content</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>Verify any publicly accessible connection to the operating system displays the Standard Mandatory DoD Notice and Consent Banner before granting access to the system.</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Fix_Text</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>Configure the operating system to display the Standard Mandatory DoD Notice and Consent Banner before granting access to the system via the ssh.</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STATUS>Not_Applicable</STATUS>
        <FINDING_DETAILS>System is not publicly accessible. Internal network only.</FINDING_DETAILS>
        <COMMENTS>N/A per system categorization - internal infrastructure only</COMMENTS>
        <SEVERITY_OVERRIDE></SEVERITY_OVERRIDE>
        <SEVERITY_JUSTIFICATION></SEVERITY_JUSTIFICATION>
      </VULN>
      <VULN>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Vuln_Num</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>V-230224</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Severity</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>high</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Group_Title</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>SRG-OS-000033-GPOS-00014</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Rule_ID</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>SV-230224r627750_rule</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Rule_Ver</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>RHEL-08-010030</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Rule_Title</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>RHEL 8 must implement NIST FIPS-validated cryptography for various purposes.</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Vuln_Discuss</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>Use of weak or untested encryption algorithms undermines the purposes of utilizing encryption to protect data.</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Check_Content</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>Verify the operating system implements DoD-approved encryption to protect the confidentiality of remote access sessions. Check to see if FIPS mode is enabled with the following command: $ fips-mode-setup --check</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STIG_DATA>
          <VULN_ATTRIBUTE>Fix_Text</VULN_ATTRIBUTE>
          <ATTRIBUTE_DATA>Configure the operating system to implement DoD-approved encryption by running the following command: $ sudo fips-mode-setup --enable</ATTRIBUTE_DATA>
        </STIG_DATA>
        <STATUS>Not_Reviewed</STATUS>
        <FINDING_DETAILS></FINDING_DETAILS>
        <COMMENTS></COMMENTS>
        <SEVERITY_OVERRIDE></SEVERITY_OVERRIDE>
        <SEVERITY_JUSTIFICATION></SEVERITY_JUSTIFICATION>
      </VULN>
    </iSTIG>
  </STIGS>
</CHECKLIST>'''
    return sample_ckl


def main():
    parser = argparse.ArgumentParser(
        description='Parse STIG Checklist (.ckl / .cklb) files for Splunk ingestion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    %(prog)s sample.ckl                     Parse .ckl and output JSON to stdout
    %(prog)s sample.cklb                    Parse .cklb and output JSON to stdout
    %(prog)s sample.ckl --output csv        Parse and output CSV to stdout
    %(prog)s sample.ckl -o output.json      Parse and write to file
    %(prog)s --generate-sample              Generate a sample .ckl file for testing
    %(prog)s --generate-sample -o test.ckl  Generate sample to specific file

Supported formats:
    .ckl   XML-based (STIG Viewer 2.x)
    .cklb  JSON-based (STIG Viewer 3.x)

Marcus House - STIG Compliance App
        '''
    )
    
    parser.add_argument('ckl_file', nargs='?', help='Path to .ckl or .cklb file to parse')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--format', '-f', choices=['json', 'csv'], default='json',
                        help='Output format (default: json)')
    parser.add_argument('--summary', '-s', action='store_true',
                        help='Print summary to stderr')
    parser.add_argument('--generate-sample', action='store_true',
                        help='Generate a sample .ckl file for testing')
    
    args = parser.parse_args()
    
    # Handle sample generation
    if args.generate_sample:
        sample = generate_sample_ckl()
        if args.output:
            with open(args.output, 'w') as f:
                f.write(sample)
            print(f"Sample .ckl file written to: {args.output}", file=sys.stderr)
        else:
            print(sample)
        return 0
    
    # Require ckl_file if not generating sample
    if not args.ckl_file:
        parser.print_help()
        return 1
    
    # Parse the file (auto-detects .ckl vs .cklb)
    events = parse_checklist_file(args.ckl_file)
    
    if not events:
        print("No events parsed from file.", file=sys.stderr)
        return 1
    
    # Print summary if requested
    if args.summary:
        print_summary(events)
    
    # Output in requested format
    if args.format == 'json':
        output_json(events, args.output)
    elif args.format == 'csv':
        output_csv(events, args.output)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
