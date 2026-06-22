#!/usr/bin/env python3
"""
CCCS Alerts Feed Collector for Splunk with MITRE ATT&CK Enrichment
Fetches Canadian Centre for Cyber Security alerts and outputs to stdout
Only sends events when the feed has changed (using hash comparison)
Parses HTML content to extract structured fields using built-in regex
Enriches alerts with MITRE ATT&CK tactics and techniques mapping
"""

import sys
import json
import hashlib
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import re
from html.parser import HTMLParser

# Get the app directory dynamically
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DIR = os.path.join(APP_DIR, 'local')

# Ensure local directory exists
if not os.path.exists(LOCAL_DIR):
    os.makedirs(LOCAL_DIR)

# Configuration
RSS_FEED_URL = "https://cyber.gc.ca/api/cccs/rss/v1/get?feed=alerts_advisories&lang=en"
ATOM_FEED_URL = "https://www.cyber.gc.ca/api/cccs/atom/v1/get?feed=alerts_advisories&lang=en"
HASH_FILE = os.path.join(LOCAL_DIR, 'cccs_feed_hash.txt')
EVENT_HASHES_FILE = os.path.join(LOCAL_DIR, 'cccs_event_hashes.json')
EVENT_RETENTION_DAYS = 31

# MITRE ATT&CK Technique Mappings
# Comprehensive mapping of keywords to MITRE ATT&CK techniques
MITRE_MAPPINGS = {
    # Initial Access (TA0001)
    'phishing': {'id': 'T1566', 'name': 'Phishing', 'tactic': 'Initial Access'},
    'spearphishing': {'id': 'T1566.001', 'name': 'Spearphishing Attachment', 'tactic': 'Initial Access'},
    'exploit public-facing': {'id': 'T1190', 'name': 'Exploit Public-Facing Application', 'tactic': 'Initial Access'},
    'drive-by': {'id': 'T1189', 'name': 'Drive-by Compromise', 'tactic': 'Initial Access'},
    'supply chain': {'id': 'T1195', 'name': 'Supply Chain Compromise', 'tactic': 'Initial Access'},
    'valid accounts': {'id': 'T1078', 'name': 'Valid Accounts', 'tactic': 'Initial Access'},
    'external remote': {'id': 'T1133', 'name': 'External Remote Services', 'tactic': 'Initial Access'},
    
    # Execution (TA0002)
    'powershell': {'id': 'T1059.001', 'name': 'PowerShell', 'tactic': 'Execution'},
    'command shell': {'id': 'T1059.003', 'name': 'Windows Command Shell', 'tactic': 'Execution'},
    'cmd.exe': {'id': 'T1059.003', 'name': 'Windows Command Shell', 'tactic': 'Execution'},
    'bash': {'id': 'T1059.004', 'name': 'Unix Shell', 'tactic': 'Execution'},
    'shell script': {'id': 'T1059.004', 'name': 'Unix Shell', 'tactic': 'Execution'},
    'python': {'id': 'T1059.006', 'name': 'Python', 'tactic': 'Execution'},
    'javascript': {'id': 'T1059.007', 'name': 'JavaScript', 'tactic': 'Execution'},
    'scheduled task': {'id': 'T1053.005', 'name': 'Scheduled Task', 'tactic': 'Execution'},
    'cron': {'id': 'T1053.003', 'name': 'Cron', 'tactic': 'Execution'},
    'windows management instrumentation': {'id': 'T1047', 'name': 'Windows Management Instrumentation', 'tactic': 'Execution'},
    'wmi': {'id': 'T1047', 'name': 'Windows Management Instrumentation', 'tactic': 'Execution'},
    
    # Persistence (TA0003)
    'registry': {'id': 'T1547.001', 'name': 'Registry Run Keys / Startup Folder', 'tactic': 'Persistence'},
    'scheduled task': {'id': 'T1053.005', 'name': 'Scheduled Task', 'tactic': 'Persistence'},
    'create account': {'id': 'T1136', 'name': 'Create Account', 'tactic': 'Persistence'},
    'bootkit': {'id': 'T1542.003', 'name': 'Bootkit', 'tactic': 'Persistence'},
    'web shell': {'id': 'T1505.003', 'name': 'Web Shell', 'tactic': 'Persistence'},
    'office application startup': {'id': 'T1137', 'name': 'Office Application Startup', 'tactic': 'Persistence'},
    
    # Privilege Escalation (TA0004)
    'privilege escalation': {'id': 'T1068', 'name': 'Exploitation for Privilege Escalation', 'tactic': 'Privilege Escalation'},
    'sudo': {'id': 'T1548.003', 'name': 'Sudo and Sudo Caching', 'tactic': 'Privilege Escalation'},
    'setuid': {'id': 'T1548.001', 'name': 'Setuid and Setgid', 'tactic': 'Privilege Escalation'},
    'bypass user account control': {'id': 'T1548.002', 'name': 'Bypass User Account Control', 'tactic': 'Privilege Escalation'},
    'access token manipulation': {'id': 'T1134', 'name': 'Access Token Manipulation', 'tactic': 'Privilege Escalation'},
    'domain policy modification': {'id': 'T1484', 'name': 'Domain Policy Modification', 'tactic': 'Privilege Escalation'},
    
    # Defense Evasion (TA0005)
    'obfuscate': {'id': 'T1027', 'name': 'Obfuscated Files or Information', 'tactic': 'Defense Evasion'},
    'disable security tools': {'id': 'T1562.001', 'name': 'Disable or Modify Tools', 'tactic': 'Defense Evasion'},
    'masquerading': {'id': 'T1036', 'name': 'Masquerading', 'tactic': 'Defense Evasion'},
    'rootkit': {'id': 'T1014', 'name': 'Rootkit', 'tactic': 'Defense Evasion'},
    'virtualization': {'id': 'T1497', 'name': 'Virtualization/Sandbox Evasion', 'tactic': 'Defense Evasion'},
    'process injection': {'id': 'T1055', 'name': 'Process Injection', 'tactic': 'Defense Evasion'},
    'indicator removal': {'id': 'T1070', 'name': 'Indicator Removal', 'tactic': 'Defense Evasion'},
    'impair defenses': {'id': 'T1562', 'name': 'Impair Defenses', 'tactic': 'Defense Evasion'},
    
    # Credential Access (TA0006)
    'credential dumping': {'id': 'T1003', 'name': 'OS Credential Dumping', 'tactic': 'Credential Access'},
    'brute force': {'id': 'T1110', 'name': 'Brute Force', 'tactic': 'Credential Access'},
    'password spray': {'id': 'T1110.003', 'name': 'Password Spraying', 'tactic': 'Credential Access'},
    'keylogging': {'id': 'T1056.001', 'name': 'Keylogging', 'tactic': 'Credential Access'},
    'input capture': {'id': 'T1056', 'name': 'Input Capture', 'tactic': 'Credential Access'},
    'lsass': {'id': 'T1003.001', 'name': 'LSASS Memory', 'tactic': 'Credential Access'},
    'mimikatz': {'id': 'T1003.001', 'name': 'LSASS Memory', 'tactic': 'Credential Access'},
    
    # Discovery (TA0007)
    'account discovery': {'id': 'T1087', 'name': 'Account Discovery', 'tactic': 'Discovery'},
    'file and directory discovery': {'id': 'T1083', 'name': 'File and Directory Discovery', 'tactic': 'Discovery'},
    'network service scanning': {'id': 'T1046', 'name': 'Network Service Scanning', 'tactic': 'Discovery'},
    'port scan': {'id': 'T1046', 'name': 'Network Service Scanning', 'tactic': 'Discovery'},
    'remote system discovery': {'id': 'T1018', 'name': 'Remote System Discovery', 'tactic': 'Discovery'},
    'system information discovery': {'id': 'T1082', 'name': 'System Information Discovery', 'tactic': 'Discovery'},
    'process discovery': {'id': 'T1057', 'name': 'Process Discovery', 'tactic': 'Discovery'},
    
    # Lateral Movement (TA0008)
    'remote desktop': {'id': 'T1021.001', 'name': 'Remote Desktop Protocol', 'tactic': 'Lateral Movement'},
    'rdp': {'id': 'T1021.001', 'name': 'Remote Desktop Protocol', 'tactic': 'Lateral Movement'},
    'ssh': {'id': 'T1021.004', 'name': 'SSH', 'tactic': 'Lateral Movement'},
    'smb': {'id': 'T1021.002', 'name': 'SMB/Windows Admin Shares', 'tactic': 'Lateral Movement'},
    'psexec': {'id': 'T1021.002', 'name': 'SMB/Windows Admin Shares', 'tactic': 'Lateral Movement'},
    'remote services': {'id': 'T1021', 'name': 'Remote Services', 'tactic': 'Lateral Movement'},
    'pass the hash': {'id': 'T1550.002', 'name': 'Pass the Hash', 'tactic': 'Lateral Movement'},
    
    # Collection (TA0009)
    'data from local system': {'id': 'T1005', 'name': 'Data from Local System', 'tactic': 'Collection'},
    'screen capture': {'id': 'T1113', 'name': 'Screen Capture', 'tactic': 'Collection'},
    'clipboard data': {'id': 'T1115', 'name': 'Clipboard Data', 'tactic': 'Collection'},
    'email collection': {'id': 'T1114', 'name': 'Email Collection', 'tactic': 'Collection'},
    'automated collection': {'id': 'T1119', 'name': 'Automated Collection', 'tactic': 'Collection'},
    
    # Command and Control (TA0011)
    'web service': {'id': 'T1102', 'name': 'Web Service', 'tactic': 'Command and Control'},
    'encrypted channel': {'id': 'T1573', 'name': 'Encrypted Channel', 'tactic': 'Command and Control'},
    'application layer protocol': {'id': 'T1071', 'name': 'Application Layer Protocol', 'tactic': 'Command and Control'},
    'dns': {'id': 'T1071.004', 'name': 'DNS', 'tactic': 'Command and Control'},
    'http': {'id': 'T1071.001', 'name': 'Web Protocols', 'tactic': 'Command and Control'},
    'https': {'id': 'T1071.001', 'name': 'Web Protocols', 'tactic': 'Command and Control'},
    'proxy': {'id': 'T1090', 'name': 'Proxy', 'tactic': 'Command and Control'},
    'remote access software': {'id': 'T1219', 'name': 'Remote Access Software', 'tactic': 'Command and Control'},
    
    # Exfiltration (TA0010)
    'exfiltration': {'id': 'T1041', 'name': 'Exfiltration Over C2 Channel', 'tactic': 'Exfiltration'},
    'data compressed': {'id': 'T1560', 'name': 'Archive Collected Data', 'tactic': 'Exfiltration'},
    'exfiltration over web service': {'id': 'T1567', 'name': 'Exfiltration Over Web Service', 'tactic': 'Exfiltration'},
    'automated exfiltration': {'id': 'T1020', 'name': 'Automated Exfiltration', 'tactic': 'Exfiltration'},
    
    # Impact (TA0040)
    'ransomware': {'id': 'T1486', 'name': 'Data Encrypted for Impact', 'tactic': 'Impact'},
    'data encrypted': {'id': 'T1486', 'name': 'Data Encrypted for Impact', 'tactic': 'Impact'},
    'data destruction': {'id': 'T1485', 'name': 'Data Destruction', 'tactic': 'Impact'},
    'denial of service': {'id': 'T1499', 'name': 'Endpoint Denial of Service', 'tactic': 'Impact'},
    'dos': {'id': 'T1499', 'name': 'Endpoint Denial of Service', 'tactic': 'Impact'},
    'ddos': {'id': 'T1498', 'name': 'Network Denial of Service', 'tactic': 'Impact'},
    'defacement': {'id': 'T1491', 'name': 'Defacement', 'tactic': 'Impact'},
    'wiper': {'id': 'T1485', 'name': 'Data Destruction', 'tactic': 'Impact'},
    'resource hijacking': {'id': 'T1496', 'name': 'Resource Hijacking', 'tactic': 'Impact'},
    'cryptomining': {'id': 'T1496', 'name': 'Resource Hijacking', 'tactic': 'Impact'},
    
    # Common vulnerability-related terms
    'remote code execution': {'id': 'T1203', 'name': 'Exploitation for Client Execution', 'tactic': 'Execution'},
    'rce': {'id': 'T1203', 'name': 'Exploitation for Client Execution', 'tactic': 'Execution'},
    'arbitrary code': {'id': 'T1203', 'name': 'Exploitation for Client Execution', 'tactic': 'Execution'},
    'code execution': {'id': 'T1203', 'name': 'Exploitation for Client Execution', 'tactic': 'Execution'},
    'buffer overflow': {'id': 'T1203', 'name': 'Exploitation for Client Execution', 'tactic': 'Execution'},
    'memory corruption': {'id': 'T1203', 'name': 'Exploitation for Client Execution', 'tactic': 'Execution'},
    'authentication bypass': {'id': 'T1078', 'name': 'Valid Accounts', 'tactic': 'Initial Access'},
    'bypass security': {'id': 'T1562', 'name': 'Impair Defenses', 'tactic': 'Defense Evasion'},
}

def calculate_hash(content):
    """Calculate SHA256 hash of content"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def read_previous_hash():
    """Read the previously stored hash"""
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_hash(hash_value):
    """Save the current hash"""
    with open(HASH_FILE, 'w') as f:
        f.write(hash_value)

def load_event_hashes():
    """Load event hashes from JSON file"""
    try:
        if os.path.exists(EVENT_HASHES_FILE):
            with open(EVENT_HASHES_FILE, 'r') as f:
                return json.load(f)
        return {}
    except:
        return {}

def save_event_hashes(hashes):
    """Save event hashes to JSON file"""
    try:
        with open(EVENT_HASHES_FILE, 'w') as f:
            json.dump(hashes, f, indent=2)
        return True
    except:
        return False

def cleanup_old_hashes(hashes):
    """Remove hashes older than EVENT_RETENTION_DAYS"""
    from datetime import timedelta
    
    cutoff_date = datetime.now() - timedelta(days=EVENT_RETENTION_DAYS)
    cleaned_hashes = {}
    
    for event_hash, timestamp_str in hashes.items():
        try:
            # Parse the timestamp
            event_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            # Keep only if within retention period
            if event_date > cutoff_date:
                cleaned_hashes[event_hash] = timestamp_str
        except:
            # If we can't parse the date, keep it to be safe
            cleaned_hashes[event_hash] = timestamp_str
    
    return cleaned_hashes

def calculate_event_hash(event):
    """Calculate hash of complete event JSON"""
    # Create a sorted JSON string for consistent hashing
    event_json = json.dumps(event, sort_keys=True)
    return hashlib.sha256(event_json.encode('utf-8')).hexdigest()

def is_event_duplicate(event_hash, event_hashes):
    """Check if event hash already exists"""
    return event_hash in event_hashes

def fetch_feed():
    """Fetch the CCCS alerts feed - tries RSS first, then Atom as fallback"""
    # Add headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; SplunkCCCSCollector/3.1; +https://www.splunk.com)',
        'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }
    
    # Try RSS feed first (seems more reliable)
    for feed_url, feed_type in [(RSS_FEED_URL, 'RSS'), (ATOM_FEED_URL, 'Atom')]:
        try:
            response = requests.get(feed_url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except:
            continue
    
    # Both feeds failed
    return None

def parse_feed(xml_content):
    """Parse the XML feed and extract entries - handles both RSS and Atom formats"""
    try:
        root = ET.fromstring(xml_content)
        
        # Detect feed type
        if root.tag == '{http://www.w3.org/2005/Atom}feed':
            # Atom feed
            return parse_atom_feed(root)
        elif root.tag == 'rss' or 'channel' in [child.tag for child in root]:
            # RSS feed
            return parse_rss_feed(root)
        else:
            return []
    except:
        return []

def parse_atom_feed(root):
    """Parse Atom feed format"""
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    entries = []
    
    for entry in root.findall('atom:entry', ns):
        item = {}
        
        # Extract ID first (used as unique identifier)
        id_elem = entry.find('atom:id', ns)
        if id_elem is not None and id_elem.text:
            item['id'] = id_elem.text.strip()
        else:
            continue  # Skip entries without ID
        
        # Extract title
        title = entry.find('atom:title', ns)
        if title is not None and title.text:
            item['title'] = title.text.strip()
        
        # Extract link (URL to the advisory)
        # Only add if different from id to avoid duplication
        link = entry.find('atom:link', ns)
        if link is not None:
            href = link.get('href')
            if href:
                href = href.strip()
                # Only add link if it's different from id
                if href != item['id']:
                    item['link'] = href
        
        # Extract alternate link only if it exists and is different from both id and link
        alt_link = entry.find("atom:link[@rel='alternate']", ns)
        if alt_link is not None:
            alt_href = alt_link.get('href')
            if alt_href:
                alt_href = alt_href.strip()
                # Only add if different from id and main link
                if alt_href != item['id'] and alt_href != item.get('link', ''):
                    item['alternate_link'] = alt_href
        
        # Extract published date
        published = entry.find('atom:published', ns)
        if published is not None and published.text:
            item['published'] = published.text.strip()
        
        # Extract updated date
        updated = entry.find('atom:updated', ns)
        if updated is not None and updated.text:
            item['updated'] = updated.text.strip()
        elif 'published' in item:
            item['updated'] = item['published']  # Fallback to published
        
        # Extract summary (only if not empty)
        summary = entry.find('atom:summary', ns)
        if summary is not None and summary.text and summary.text.strip():
            item['summary'] = summary.text.strip()
        
        # Extract content (full advisory text)
        content = entry.find('atom:content', ns)
        if content is not None:
            content_text = content.text
            if content_text and content_text.strip():
                item['content'] = content_text.strip()
                # Get content type attribute
                content_type = content.get('type')
                if content_type:
                    item['content_type'] = content_type
        
        # Extract author
        author = entry.find('atom:author', ns)
        if author is not None:
            author_name = author.find('atom:name', ns)
            if author_name is not None and author_name.text:
                item['author'] = author_name.text.strip()
        
        # Default author if not found
        if not item.get('author'):
            item['author'] = 'Canadian Centre for Cyber Security'
        
        entries.append(item)
    
    return entries

def parse_rss_feed(root):
    """Parse RSS feed format"""
    entries = []
    
    # Find channel element
    channel = root.find('channel') if root.tag == 'rss' else root
    
    for item_elem in channel.findall('item'):
        item = {}
        
        # Extract link and use it as id (RSS standard - link is the identifier)
        link_elem = item_elem.find('link')
        if link_elem is not None and link_elem.text:
            link_url = link_elem.text.strip()
            # For RSS, we use the link as the 'id' field for consistency
            item['id'] = link_url
            # Don't add 'link' separately to avoid duplication
        else:
            # Skip items without links
            continue
        
        # Extract title
        title = item_elem.find('title')
        item['title'] = title.text.strip() if title is not None and title.text else ''
        
        # Extract pubDate - try multiple date fields
        pub_date = item_elem.find('pubDate')
        if pub_date is not None and pub_date.text:
            item['published'] = pub_date.text.strip()
        
        # For RSS, updated is often in a different field or same as published
        # Check for dc:date or other update fields (with namespace)
        updated = item_elem.find('{http://purl.org/dc/elements/1.1/}date')
        if updated is not None and updated.text:
            item['updated'] = updated.text.strip()
        elif 'published' in item:
            item['updated'] = item['published']  # Fallback to published date
        
        # Extract description (RSS equivalent of summary/content)
        description = item_elem.find('description')
        if description is not None and description.text:
            desc_text = description.text.strip()
            item['summary'] = desc_text
            # Only set content if it's substantial (likely HTML)
            if len(desc_text) > 100 or '<' in desc_text:
                item['content'] = desc_text
        
        # Extract author if available
        author = item_elem.find('author')
        if author is not None and author.text:
            item['author'] = author.text.strip()
        elif not item.get('author'):
            # Default author for CCCS feeds
            item['author'] = 'Canadian Centre for Cyber Security'
        
        entries.append(item)
    
    return entries

def parse_html_content(html_content):
    """Parse HTML content to extract structured fields using regex (no external deps)"""
    if not html_content:
        return {}
    
    try:
        parsed = {}
        
        # Remove HTML comments
        html_content = re.sub(r'<!--.*?-->', '', html_content, flags=re.DOTALL)
        
        # Extract serial number
        serial_match = re.search(r'<strong>Serial number:\s*</strong>\s*([A-Z]{2}\d{2}-\d+)', html_content, re.IGNORECASE)
        if serial_match:
            parsed['serial_number'] = serial_match.group(1).strip()
        
        # Extract date
        date_match = re.search(r'<strong>Date:\s*</strong>\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})', html_content, re.IGNORECASE)
        if date_match:
            parsed['date'] = date_match.group(1).strip()
        
        # Extract all paragraph text (removing HTML tags)
        paragraphs = []
        p_matches = re.findall(r'<p>(.*?)</p>', html_content, re.DOTALL | re.IGNORECASE)
        for p in p_matches:
            # Remove all HTML tags from paragraph
            text = re.sub(r'<[^>]+>', '', p)
            # Remove special characters and extra whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            # Decode HTML entities
            text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            # Skip metadata paragraphs
            if text and not re.match(r'^(Serial number:|Date:)', text, re.IGNORECASE) and len(text) > 20:
                paragraphs.append(text)
        
        if paragraphs:
            # Take first 2 meaningful paragraphs as array
            parsed['summary_text'] = paragraphs[:2]
        
        # Extract recommendations - look for "Cyber Centre encourages/recommends" paragraphs
        recommendations = []
        recommendation_keywords = [
            r'Cyber Centre encourages',
            r'Cyber Centre recommends',
            r'CCCS encourages',
            r'CCCS recommends',
            r'users and administrators',
            r'strongly recommends',
            r'advises users'
        ]
        
        for p in paragraphs:
            for keyword in recommendation_keywords:
                if re.search(keyword, p, re.IGNORECASE):
                    # Clean up the recommendation text
                    rec_text = p.strip()
                    if rec_text and rec_text not in recommendations:
                        recommendations.append(rec_text)
                    break
        
        if recommendations:
            parsed['recommendations'] = recommendations
        
        # Extract affected products from list items (not in reference lists)
        affected_products = []
        
        # Find all <ul> sections that are NOT reference lists
        ul_sections = re.findall(r'<ul(?:\s+class="[^"]*")?>.*?</ul>', html_content, re.DOTALL | re.IGNORECASE)
        
        for ul in ul_sections:
            # Skip if it's a reference list (has class="list-unstyled" or contains <a> tags)
            if 'list-unstyled' in ul or '<a' in ul:
                continue
            
            # Extract <li> items
            li_items = re.findall(r'<li>(.*?)</li>', ul, re.DOTALL | re.IGNORECASE)
            for li in li_items:
                # Remove HTML tags
                text = re.sub(r'<[^>]+>', '', li)
                # Clean up whitespace and entities
                text = re.sub(r'\s+', ' ', text).strip()
                text = text.replace('&nbsp;', ' ').replace('&#8211;', '–').replace('&#x2013;', '–')
                
                if text:
                    # Try to split product and version using common separators
                    match = re.match(r'(.+?)\s*[–—-]\s*(.+)', text)
                    if match:
                        product_name = match.group(1).strip()
                        version_info = match.group(2).strip()
                        
                        # Parse version_info into an array
                        # Split on common delimiters: comma, "and", semicolon
                        version_parts = re.split(r'[,;]|\s+and\s+', version_info)
                        # Clean up each version part
                        versions_array = [v.strip() for v in version_parts if v.strip()]
                        
                        affected_products.append({
                            'product': product_name,
                            'affected_versions': versions_array
                        })
                    else:
                        affected_products.append({'product': text})
        
        if affected_products:
            parsed['affected_products'] = affected_products
        
        # Extract CVEs
        cve_pattern = re.compile(r'CVE-\d{4}-\d{4,7}', re.IGNORECASE)
        cves_found = cve_pattern.findall(html_content)
        if cves_found:
            # Convert to uppercase and deduplicate
            parsed['cves'] = list(set([cve.upper() for cve in cves_found]))
        
        # Check for exploit mentions
        exploit_keywords = [
            r'exploit', r'actively exploited', r'in the wild', 
            r'weaponized', r'exploitation', r'being exploited'
        ]
        
        # Get text without tags for searching
        text_only = re.sub(r'<[^>]+>', '', html_content).lower()
        
        for keyword in exploit_keywords:
            if re.search(keyword, text_only, re.IGNORECASE):
                parsed['exploit_mentioned'] = True
                # Try to extract context (50 chars before and after)
                context_match = re.search(rf'.{{0,50}}{keyword}.{{0,50}}', text_only, re.IGNORECASE)
                if context_match:
                    parsed['exploit_context'] = context_match.group(0).strip()
                break
        
        # Extract references from list-unstyled lists
        references = []
        
        # Find ul with class="list-unstyled"
        ref_lists = re.findall(r'<ul\s+class="list-unstyled"[^>]*>(.*?)</ul>', html_content, re.DOTALL | re.IGNORECASE)
        
        for ul in ref_lists:
            # Extract <a> tags with href and text
            links = re.findall(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', ul, re.IGNORECASE)
            for href, name in links:
                # Clean up the name (remove tags if any)
                name_clean = re.sub(r'<[^>]+>', '', name).strip()
                if href and name_clean:
                    references.append({
                        'name': name_clean,
                        'url': href
                    })
        
        if references:
            parsed['references'] = references
        
        # Extract source URL from article tag
        article_match = re.search(r'<article[^>]+about="([^"]+)"', html_content, re.IGNORECASE)
        if article_match:
            parsed['source_path'] = article_match.group(1)
        
        return parsed
        
    except Exception as e:
        # Log errors to stderr for debugging
        print(f"Error parsing HTML content: {e}", file=sys.stderr)
        return {}

def extract_mitre_techniques(alert_content):
    """
    Extract MITRE ATT&CK techniques from alert content
    Returns dict with techniques, tactics, and metadata
    """
    techniques = []
    tactics_found = set()
    technique_ids_found = set()
    
    # Normalize content for searching
    content_lower = alert_content.lower()
    
    # Search for techniques by keywords
    for keyword, technique in MITRE_MAPPINGS.items():
        if keyword in content_lower:
            # Avoid duplicates
            if technique['id'] not in technique_ids_found:
                techniques.append({
                    'id': technique['id'],
                    'name': technique['name'],
                    'tactic': technique['tactic'],
                    'detection_method': 'keyword',
                    'keyword': keyword
                })
                tactics_found.add(technique['tactic'])
                technique_ids_found.add(technique['id'])
    
    # Search for explicit MITRE technique references (T1234 or T1234.001)
    pattern = re.compile(r'\b(T\d{4}(?:\.\d{3})?)\b', re.IGNORECASE)
    explicit_techniques = pattern.findall(alert_content)
    
    for tid in explicit_techniques:
        tid_upper = tid.upper()
        if tid_upper not in technique_ids_found:
            techniques.append({
                'id': tid_upper,
                'name': 'Explicit Reference',
                'detection_method': 'explicit',
                'source': 'alert_content'
            })
            technique_ids_found.add(tid_upper)
    
    # Determine attack complexity based on number of techniques
    complexity = 'simple'
    if len(techniques) >= 5:
        complexity = 'complex'
    elif len(techniques) >= 3:
        complexity = 'moderate'
    
    # Calculate threat score (0-100)
    # Based on: number of techniques, tactics diversity, critical techniques
    threat_score = 0
    
    # Base score from technique count
    threat_score += min(len(techniques) * 5, 40)
    
    # Bonus for tactic diversity
    threat_score += min(len(tactics_found) * 8, 32)
    
    # Critical technique bonus
    critical_techniques = {'T1190', 'T1068', 'T1486', 'T1003', 'T1078'}
    for tech in techniques:
        if tech['id'] in critical_techniques:
            threat_score += 7
    
    threat_score = min(threat_score, 100)
    
    # Determine severity based on threat score
    if threat_score >= 70:
        severity = 'critical'
    elif threat_score >= 50:
        severity = 'high'
    elif threat_score >= 30:
        severity = 'medium'
    else:
        severity = 'low'
    
    return {
        'techniques': techniques,
        'tactics': sorted(list(tactics_found)),
        'technique_count': len(techniques),
        'tactic_count': len(tactics_found),
        'attack_complexity': complexity,
        'threat_score': threat_score,
        'mitre_severity': severity
    }

def send_to_splunk(events, event_hashes):
    """Output events to stdout for Splunk scripted input with deduplication"""
    sent_count = 0
    duplicate_count = 0
    new_hashes = {}
    current_timestamp = datetime.now().isoformat() + 'Z'
    
    for event in events:
        # Parse HTML content if present
        if 'content' in event and event['content']:
            parsed_content = parse_html_content(event['content'])
            # Merge parsed content into event
            event.update(parsed_content)
            # Remove the HTML content field after parsing
            del event['content']
        
        # MITRE ATT&CK Enrichment
        # Collect all relevant text fields for analysis
        text_for_analysis = []
        
        # Add various text fields
        if 'title' in event:
            text_for_analysis.append(event['title'])
        if 'summary' in event:
            text_for_analysis.append(event['summary'])
        if 'summary_text' in event and isinstance(event['summary_text'], list):
            text_for_analysis.extend(event['summary_text'])
        if 'recommendations' in event and isinstance(event['recommendations'], list):
            text_for_analysis.extend(event['recommendations'])
        if 'exploit_context' in event:
            text_for_analysis.append(event['exploit_context'])
        
        # Combine all text
        full_text = ' '.join(text_for_analysis)
        
        # Extract MITRE techniques if we have text to analyze
        if full_text.strip():
            mitre_data = extract_mitre_techniques(full_text)
            
            # Only add MITRE data if techniques were found
            if mitre_data['techniques']:
                event['mitre_techniques'] = mitre_data['techniques']
                event['mitre_tactics'] = mitre_data['tactics']
                event['mitre_technique_count'] = mitre_data['technique_count']
                event['mitre_tactic_count'] = mitre_data['tactic_count']
                event['mitre_attack_complexity'] = mitre_data['attack_complexity']
                event['mitre_threat_score'] = mitre_data['threat_score']
                event['mitre_severity'] = mitre_data['mitre_severity']
                
                # Add enrichment flag
                event['mitre_enriched'] = True
        
        # Calculate hash of the complete event
        event_hash = calculate_event_hash(event)
        
        # Check if this event was already sent (deduplication)
        if is_event_duplicate(event_hash, event_hashes):
            duplicate_count += 1
            continue  # Skip this event
        
        # Output as JSON to stdout - Splunk will capture this
        print(json.dumps(event))
        sys.stdout.flush()
        
        # Track this event hash with current timestamp
        new_hashes[event_hash] = current_timestamp
        sent_count += 1
    
    return sent_count, duplicate_count, new_hashes


def main():
    """Main function"""
    # Load existing event hashes
    event_hashes = load_event_hashes()
    
    # Cleanup old hashes (older than 5 days)
    event_hashes = cleanup_old_hashes(event_hashes)
    
    # Fetch the feed
    xml_content = fetch_feed()
    if not xml_content:
        sys.exit(1)
    
    # Calculate hash of current content
    current_hash = calculate_hash(xml_content)
    previous_hash = read_previous_hash()
    
    # Check if content has changed at feed level (first validation)
    if current_hash == previous_hash:
        # Feed hasn't changed, but still save cleaned hashes
        save_event_hashes(event_hashes)
        sys.exit(0)
    
    # Parse the feed
    entries = parse_feed(xml_content)
    
    if entries:
        # Send to Splunk with event-level deduplication (second validation)
        sent_count, duplicate_count, new_hashes = send_to_splunk(entries, event_hashes)
        
        # Merge new hashes with existing ones
        event_hashes.update(new_hashes)
        
        # Save the updated event hashes
        save_event_hashes(event_hashes)
        
        # Save the new feed hash only if we processed events
        save_hash(current_hash)
        
        # Log statistics (will appear in Splunk's _internal logs)
        sys.stderr.write(f"CCCS Collector: Processed {len(entries)} events, sent {sent_count} new events, skipped {duplicate_count} duplicates\n")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
