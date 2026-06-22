#!/usr/bin/env python3
"""
Diagnostic script to test if the modular input is working correctly.
Run this to verify the nucleus_logs.py script can be introspected.

Usage:
    $SPLUNK_HOME/bin/splunk cmd python3 test_modular_input.py
"""

import sys
import os

# Add bin directory to path for vendored packages
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Nucleus Logs Modular Input Diagnostic Test")
print("=" * 60)

# Test 1: Check Python version
print(f"\n1. Python Version: {sys.version}")

# Test 2: Check if splunklib is available
try:
    from splunklib.modularinput import Script
    print("2. splunklib.modularinput: ✓ Available")
except ImportError as e:
    print(f"2. splunklib.modularinput: ✗ Error: {e}")
    sys.exit(1)

# Test 3: Check if requests is available
try:
    import requests
    print(f"3. requests library: ✓ Available (version {requests.__version__})")
except ImportError as e:
    print(f"3. requests library: ✗ Error: {e}")

# Test 4: Try to import the nucleus_logs module
try:
    import nucleus_logs
    print("4. nucleus_logs module: ✓ Importable")
except ImportError as e:
    print(f"4. nucleus_logs module: ✗ Error: {e}")
    sys.exit(1)

# Test 5: Check if NucleusLogsInput class exists
try:
    input_class = nucleus_logs.NucleusLogsInput()
    print("5. NucleusLogsInput class: ✓ Instantiable")
except Exception as e:
    print(f"5. NucleusLogsInput class: ✗ Error: {e}")
    sys.exit(1)

# Test 6: Check if get_scheme method exists
try:
    scheme = input_class.get_scheme()
    print(f"6. get_scheme method: ✓ Returns scheme")
    print(f"   - Title: {scheme.title}")
    print(f"   - Description: {scheme.description}")
    print(f"   - Arguments: {len(scheme.arguments)} defined")
    for arg in scheme.arguments:
        print(f"     - {arg.name} (required: {arg.required_on_create})")
except Exception as e:
    print(f"6. get_scheme method: ✗ Error: {e}")
    sys.exit(1)

# Test 7: Test scheme XML generation
try:
    import io
    xml_output = io.StringIO()
    scheme.to_xml(xml_output)
    xml_str = xml_output.getvalue()
    print(f"7. Scheme XML generation: ✓ Success ({len(xml_str)} bytes)")
    if len(xml_str) > 0:
        print("   First 200 characters:")
        print(f"   {xml_str[:200]}...")
except Exception as e:
    print(f"7. Scheme XML generation: ✗ Error: {e}")

print("\n" + "=" * 60)
print("Diagnostic Test Complete")
print("=" * 60)
print("\nIf all tests passed, the modular input script is working correctly.")
print("If it's not appearing in Splunk UI, check:")
print("1. App is enabled in Splunk")
print("2. inputs.conf has [nucleus_logs] stanza with python.version=python3")
print("3. Splunk has been restarted after installation")
print("4. Check splunkd.log for any errors during app loading")
