import os
import sys
from modinput_ninja import modinput_ninja

# Scheme of user-editable variables (mandatory for splunklib)
INPUT_SCHEME_JSON = {
    "title": "Admin Ninja: License Pools",
    "description": "Get the current status/configuration of Splunk license pools in your environment.",
    "use_external_validation": False,
    "streaming_mode": "simple",
    "args": [
        {
            "name": "maximum_entries",
            "description": "Limits number of entries returned. (In all cases but testing, this should be 0)", 
            "title": "Maximum entries", 
            "required_on_create": True,
            "required_on_edit": True, 
            "data_type": "number", 
            "validation": "is_nonneg_int('maximum_entries')"
        }
    ]
}

if __name__ == "__main__":
    # scheme of NON user-editable variables - these should be changed by script writer per API endpoint, to suit class modinput_ninja
    vars = {
        "uri_path": "/servicesNS/-/-/licenser/pools",
        "uri_query": {
            'output_mode': 'json'
        },
        "target_host": "127.0.0.1",
        "target_port": 8089,
        "path_list": [
            "entry[*].name", 
            "entry[*].content"
        ]
    }
    modinput = modinput_ninja("ninja_license_pools", INPUT_SCHEME_JSON, vars)
    sys.exit(modinput.run(sys.argv))