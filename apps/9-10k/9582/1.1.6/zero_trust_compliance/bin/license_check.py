#!/usr/bin/env python3
# ==============================================================================
# ZERO TRUST COMPLIANCE - TIER VALIDATION (CUSTOM SEARCH COMMAND)
# ==============================================================================

import os
import sys

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
LIB_DIR = os.path.join(BIN_DIR, 'lib')
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

try:
    from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

if SDK_AVAILABLE:
    @Configuration()
    class ZTValidateCommand(GeneratingCommand):
        def generate(self):
            yield {
                'license_tier': 'Open_Source_Community',
                'app_name': 'Zero Trust Compliance & IMS',
                'version': '1.0.0',
                'cloud_ready': 'True',
                'status': 'Active'
            }

    if __name__ == '__main__':
        dispatch(ZTValidateCommand, sys.argv, sys.stdin, sys.stdout, __name__)
else:
    if __name__ == '__main__':
        print("Tier: Open_Source_Community, Status: Active")
