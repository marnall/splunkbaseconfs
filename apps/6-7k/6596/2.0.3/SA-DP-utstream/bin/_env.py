#!/usr/bin/env @PYTHON_EXECUTABLE@
#
# File: _env.py - Version 2.0.3
# Copyright © Datapunctum AG 2023-6-28
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import os

DEFAULTPREFIX = "utstream"

CONFIG = {
    "APP_NAME": "SA-DP-utstream",
    "APP_VERSION": "2.0.3",
    "DEFAULT_OWNER": "nobody",
    "PRODUCT_IDENTIFIER": "utstream",
    "SPLUNK_HOME": os.environ["SPLUNK_HOME"],
    "LICENSE_FILE_NAME": "utstream_licenses",
    "SETTINGS_FILE_NAME": "utstream_settings",
    "LOGGING_FILE_NAME": "utstream_logging",
    "CRIBL_INSTANCE_FILE_NAME": "utstream_instance",
    "CRIBL_INSTANCE_LIST_ROLES": ["utstream_reader"],
    "CRIBL_INSTANCE_EDIT_ROLES": ["utstream_admin"],
    "CRIBL_REPLAY_FILE_NAME": "utstream_inputs",
    "CRIBL_REPLAY_LIST_ROLES": ["utstream_reader"],
    "CRIBL_REPLAY_EDIT_ROLES": ["utstream_admin"],
    "ADMIN_ROLES": ["admin", "sc_admin", "utstream_admin"],
    "UTSTREAM_COLLECTIONS": {
        "utstream_discovery_jobs_collection": "utstream_discovery_jobs",
        "utstream_discovery_inventory_collection": "utstream_discovery_inventory",
        "utstream_discovery_results_collection": "utstream_discovery_results",
        "utstream_replay_jobs_collection": "utstream_replay_jobs",
        "utstream_replay_results_collection": "utstream_replay_results",
    },
}
