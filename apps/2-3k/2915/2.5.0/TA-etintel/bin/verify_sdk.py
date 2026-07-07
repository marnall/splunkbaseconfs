#!/usr/bin/env python

import sys
import os

# Add the current directory to the path so we can import the app module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ta_etintel', 'aob_py3'))

try:
    import splunklib
    print(f"Splunklib found in: {splunklib.__file__}")
    
    # Check if we can import the version
    try:
        print(f"Splunklib version: {splunklib.__version__}")
    except AttributeError:
        # Try to get version from the package
        try:
            import pkg_resources
            version = pkg_resources.get_distribution("splunk-sdk").version
            print(f"Splunklib version (from pkg_resources): {version}")
        except Exception as e:
            print(f"Unable to determine version: {e}")
            
    # Check for dependencies
    try:
        import deprecation
        print(f"Deprecation package found: {deprecation.__file__}")
    except ImportError:
        print("Warning: Deprecation package not found")
        
    try:
        import packaging
        print(f"Packaging package found: {packaging.__file__}")
    except ImportError:
        print("Warning: Packaging package not found")
    
    # Test that we can import the key modules used in the app
    from splunklib import client
    print("Successfully imported splunklib.client")
    
    from splunklib import binding
    print("Successfully imported splunklib.binding")
    
    from splunklib import modularinput
    print("Successfully imported splunklib.modularinput")
    
    print("\nSDK verification completed successfully!")
    
except ImportError as e:
    print(f"Error: {e}")
    print("SDK verification failed!") 