#!/usr/bin/env python3
"""
Simplified Nucleus Security Logs Modular Input - for debugging
"""

import sys
import os

# Write diagnostic info
sys.stderr.write("=== Nucleus Logs Script Diagnostic ===\n")
sys.stderr.write(f"Python version: {sys.version}\n")
sys.stderr.write(f"Script path: {__file__}\n")
sys.stderr.write(f"Working directory: {os.getcwd()}\n")
sys.stderr.write(f"Arguments: {sys.argv}\n")

# Add bin directory to path
bin_dir = os.path.dirname(os.path.abspath(__file__))
sys.stderr.write(f"Bin directory: {bin_dir}\n")

if bin_dir not in sys.path:
    sys.path.insert(0, bin_dir)

sys.stderr.write(f"sys.path: {sys.path}\n")

# Test imports one by one
try:
    sys.stderr.write("Testing import: json... ")
    import json
    sys.stderr.write("OK\n")
except Exception as e:
    sys.stderr.write(f"FAILED: {e}\n")
    sys.exit(1)

try:
    sys.stderr.write("Testing import: requests... ")
    import requests
    sys.stderr.write(f"OK (version {requests.__version__})\n")
except Exception as e:
    sys.stderr.write(f"FAILED: {e}\n")
    sys.exit(1)

try:
    sys.stderr.write("Testing import: splunklib.modularinput... ")
    from splunklib.modularinput import Script, Scheme, Argument
    sys.stderr.write("OK\n")
except Exception as e:
    sys.stderr.write(f"FAILED: {e}\n")
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

sys.stderr.write("=== All imports successful ===\n")

# Now try to import the actual script
try:
    sys.stderr.write("Attempting to import nucleus_logs module... ")
    import nucleus_logs
    sys.stderr.write("OK\n")
    
    sys.stderr.write("Creating NucleusLogsInput instance... ")
    input_instance = nucleus_logs.NucleusLogsInput()
    sys.stderr.write("OK\n")
    
    sys.stderr.write("Getting scheme... ")
    scheme = input_instance.get_scheme()
    sys.stderr.write(f"OK (title: {scheme.title})\n")
    
    sys.stderr.write("=== Script validation successful ===\n")
    
except Exception as e:
    sys.stderr.write(f"FAILED: {e}\n")
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

sys.exit(0)
