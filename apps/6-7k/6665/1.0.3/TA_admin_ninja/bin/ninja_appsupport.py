import os
import sys
from modinput_splunkbase import modinput_splunkbase

# Scheme of user-editable variables (mandatory for splunklib)
INPUT_SCHEME_JSON = {
    "title": "Admin Ninja: App Support Details",
    "description": "Get data from Splunkbase about the version support & support type of Apps installed in your environment.",
    "use_external_validation": True,
    "streaming_mode": "simple",
    "args": [
        {
            "name": "apps_lookup",
            "description": "Please enter the lookup file with a unique list of apps installed in your environment. Admin Ninja App provides one: 'admin_ninja_unique_apps.csv' The lookup file CANNOT be private.", 
            "title": "Unique App List Lookup", 
            "required_on_create": True,
            "required_on_edit": True, 
            "data_type": "string", 
            "validation": None            
        },
        {
            "name": "lookup_located_app",
            "description": "Please enter the app FOLDER NAME that houses the previously entered lookup file.", 
            "title": "App Lookup is located in", 
            "required_on_create": True,
            "required_on_edit": True, 
            "data_type": "string", 
            "validation": None
        }
    ]
}

if __name__ == "__main__":
    # scheme of NON user-editable variables - these should be changed by script writer per API endpoint, to suit class modinput_ninja
    modinput = modinput_splunkbase("ninja_appsupport", INPUT_SCHEME_JSON)
    sys.exit(modinput.run(sys.argv))