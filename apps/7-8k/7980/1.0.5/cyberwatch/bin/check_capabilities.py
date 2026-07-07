#!/usr/bin/env python

import sys
import splunk.rest as rest
import json

def check_capabilities():
    """Check if required capabilities are present in admin role"""
    try:
        required_capabilities = [
            'admin_all_objects',
            'edit_alert_actions',
            'edit_search_schedule',
            'list_search',
            'schedule_search',
            'write_alert_actions'
        ]

        # Get admin role capabilities
        _, serverContent = rest.simpleRequest(
            "/services/authorization/roles/admin",
            method='GET',
            getargs={'output_mode': 'json'},
            raiseAllErrors=True
        )

        role_data = json.loads(serverContent)
        if 'entry' in role_data and len(role_data['entry']) > 0:
            capabilities = role_data['entry'][0]['content'].get('capabilities', [])
            
            print("\nChecking admin role capabilities:")
            print("---------------------------------")
            all_present = True
            for cap in required_capabilities:
                if cap in capabilities:
                    print(f"✓ {cap:<20} - Present")
                else:
                    print(f"✗ {cap:<20} - Missing")
                    all_present = False
            
            if all_present:
                print("\nAll required capabilities are present.")
                return True
            else:
                print("\nSome capabilities are missing. Please add them to the admin role.")
                return False

    except Exception as e:
        print(f"Error checking capabilities: {str(e)}")
        return False

if __name__ == "__main__":
    if check_capabilities():
        sys.exit(0)
    else:
        sys.exit(1) 