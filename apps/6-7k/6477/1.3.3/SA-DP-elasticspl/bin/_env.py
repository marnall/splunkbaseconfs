#!/usr/bin/env python3
#
# File: _env.py - Version 1.3.3
# Copyright © Datapunctum AG 2026-2-11
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import os

DEFAULTPREFIX = "elasticspl"

CONFIG = {
    "APP_NAME": "SA-DP-elasticspl",
    "PRODUCT_IDENTIFIER": "elasticspl",
    "APP_VERSION": "1.3.3",
    "DEFAULT_OWNER": "nobody",
    "SPLUNK_HOME": os.environ["SPLUNK_HOME"],
    "LICENSE_FILE_NAME": "elasticspl_licenses",
    "SETTINGS_FILE_NAME": "elasticspl_settings",
    "LOGGING_FILE_NAME": "elasticspl_logging",
    "ADMIN_ROLES": ["admin", "sc_admin", "elastic_admin"],
    "ELASTIC_INSTANCE_READ_ROLES": ["elastic_user"],
    "ELASTIC_INSTANCE_WRITE_ROLES": ["elastic_admin"],
    "ELASTIC_QUERY_READ_ROLES": ["elastic_user"],
    "ELASTIC_QUERY_WRITE_ROLES": ["elastic_power"],
    "ELASTIC_COMMAND_ADHOC_ROLES": ["elastic_adhoc"],
    "ELASTIC_COMMAND_SAVED_ROLES": ["elastic_user"],
    "ELASTIC_INSTANCE": "elastic_instance",
    "ELASTIC_QUERY": "elastic_query",
}
