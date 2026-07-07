#!/usr/bin/env python
# This script checks imports to ensure all required modules are available after the SDK upgrade

import sys
import os

# Add the app's bin directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ta_etintel_declare

print("Checking imports for Splunk SDK 2.1.0...")

try:
    # Import the main SDK modules
    import splunklib
    print(f"✓ Successfully imported splunklib")
    
    # Try to get the version
    try:
        print(f"  - Version: {splunklib.__version__}")
    except AttributeError:
        print("  - Version: unknown (no __version__ attribute)")
    
    from splunklib import client
    print("✓ Successfully imported splunklib.client")
    
    from splunklib import binding
    print("✓ Successfully imported splunklib.binding")
    
    from splunklib import modularinput
    print("✓ Successfully imported splunklib.modularinput")
    
except ImportError as e:
    print(f"✘ Error importing splunklib: {e}")

try:
    # Import the new dependencies 
    import deprecation
    print("✓ Successfully imported deprecation")
    try:
        print(f"  - Version: {deprecation.__version__}")
    except AttributeError:
        print("  - Version: unknown (no __version__ attribute)")
except ImportError as e:
    print(f"✘ Error importing deprecation: {e}")

try:
    import packaging
    print("✓ Successfully imported packaging")
    try:
        print(f"  - Version: {packaging.__version__}")
    except AttributeError:
        print("  - Version: unknown (no __version__ attribute)")
except ImportError as e:
    print(f"✘ Error importing packaging: {e}")

try:
    # Test modular input import
    from splunklib import modularinput as smi
    print("✓ Successfully imported modularinput")
except ImportError as e:
    print(f"✘ Error importing modularinput: {e}")

# Check some common app imports
try:
    import modinput_wrapper.base_modinput
    print("✓ Successfully imported modinput_wrapper")
except ImportError as e:
    print(f"✘ Error importing modinput_wrapper: {e}")

try:
    import input_module_update_repdata
    print("✓ Successfully imported update_repdata module")
except ImportError as e: 
    print(f"✘ Error importing update_repdata: {e}")

print("\nImport check completed.") 