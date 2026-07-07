#!/usr/bin/env python3.7
#
# File: _env.py - Version 1.0.4
# Copyright © Datapunctum AG 2024-11-22
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import os

DEFAULTPREFIX = "s3spl"

CONFIG = {
    "APP_NAME": "SA-DP-s3spl",
    "PRODUCT_IDENTIFIER": "s3spl",
    "APP_VERSION": "1.0.4",
    "DEFAULT_OWNER": "nobody",
    "SPLUNK_HOME": os.environ["SPLUNK_HOME"],
    "LICENSE_FILE_NAME": "s3spl_licenses",
    "SETTINGS_FILE_NAME": "s3spl_settings",
    "LOGGING_FILE_NAME": "s3spl_logging",
    "ADMIN_ROLES": ["admin", "sc_admin", "s3spl_admin"],
    "S3SPL_BUCKET_READ_ROLES": ["s3spl_user"],
    "S3SPL_BUCKET_WRITE_ROLES": ["s3spl_admin"],
    "S3SPL_QUERY_READ_ROLES": ["s3spl_user"],
    "S3SPL_QUERY_WRITE_ROLES": ["s3spl_power"],
    "S3SPL_COMMAND_ADHOC_ROLES": ["s3spl_adhoc"],
    "S3SPL_COMMAND_SAVED_ROLES": ["s3spl_user"],
    "S3SPL_BUCKET": "s3spl_bucket",
    "S3SPL_QUERY": "s3spl_query",
}
