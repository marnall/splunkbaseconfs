#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Splunk Version Checker for SOCRadar Apps
This script logs the Splunk version when the app starts
"""

import sys
import os
import json

# Add Splunk Python SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

def get_splunk_version(helper=None):
    """
    Get Splunk version information
    
    Returns:
        dict: Version information including version, build, and compatibility notes
    """
    version_info = {
        "version": "unknown",
        "build": "unknown",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "compatibility_notes": []
    }
    
    try:
        # Method 1: Try to get from splunkd
        import splunk.rest as rest
        
        response = rest.simpleRequest('/services/server/info', 
                                    sessionKey=helper.session_key if helper else None,
                                    getargs={'output_mode': 'json'})
        
        if response[0].status == 200:
            data = json.loads(response[1])
            if 'entry' in data and len(data['entry']) > 0:
                content = data['entry'][0].get('content', {})
                version_info['version'] = content.get('version', 'unknown')
                version_info['build'] = content.get('build', 'unknown')
    except:
        pass
    
    # Alternative: Check environment variables
    if version_info['version'] == "unknown":
        splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
        version_file = os.path.join(splunk_home, 'etc', 'splunk.version')
        
        try:
            with open(version_file, 'r') as f:
                for line in f:
                    if line.startswith('VERSION='):
                        version_info['version'] = line.split('=')[1].strip()
                    elif line.startswith('BUILD='):
                        version_info['build'] = line.split('=')[1].strip()
        except:
            pass
    
    # Add compatibility notes based on version
    if version_info['version'] != "unknown":
        major_version = version_info['version'].split('.')[0]
        
        if major_version == "7":
            version_info['compatibility_notes'].append("Dashboard column alignment may not be supported")
            version_info['compatibility_notes'].append("Python 2.7 environment")
        elif major_version == "8":
            minor_version = version_info['version'].split('.')[1] if '.' in version_info['version'] else "0"
            if int(minor_version) < 2:
                version_info['compatibility_notes'].append("Python 2.7 or 3.7 environment")
            else:
                version_info['compatibility_notes'].append("Python 3.7+ environment")
        elif major_version == "9":
            version_info['compatibility_notes'].append("Full dashboard feature support")
            version_info['compatibility_notes'].append("Python 3 only environment")
    
    return version_info

def log_version_info(helper):
    """
    Log Splunk version information to help with debugging
    
    Args:
        helper: Splunk helper object for logging
    """
    version_info = get_splunk_version(helper)
    
    helper.log_info("=" * 60)
    helper.log_info("SPLUNK VERSION INFORMATION")
    helper.log_info(f"Splunk Version: {version_info['version']}")
    helper.log_info(f"Splunk Build: {version_info['build']}")
    helper.log_info(f"Python Version: {version_info['python_version']}")
    
    if version_info['compatibility_notes']:
        helper.log_info("Compatibility Notes:")
        for note in version_info['compatibility_notes']:
            helper.log_info(f"  - {note}")
    
    helper.log_info("=" * 60)
    
    return version_info

# For testing standalone
if __name__ == "__main__":
    info = get_splunk_version()
    print(json.dumps(info, indent=2))