#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This file consists constants used in the /bin module
"""
import os.path as op

APP_NAME = __file__.split(op.sep)[-3]
CONNECTION_ERROR = "log_connection_error"
CONFIGURATION_ERROR = "log_configuration_error"
PERMISSION_ERROR = "log_permission_error"
AUTHENTICATION_ERROR = "log_authentication_error"
PASSWORD_EXPIRED_ERROR = "log_password_expired_error"
SERVER_ERROR = "log_server_error"
GENERAL_EXCEPTION = "log_exception"
CYBERARK_EPM_ERROR = "cyberark_epm_ta_error"
UCC_EXECPTION_EXE_LABEL = "splunk_ta_cyberark_epm_exception_{}"
PAGE_LIMIT = 500
ACCOUNT_ADMIN_SOURCETYPE = "cyberark:epm:account:admin:audit"
API_TIME_OUT = 120
# Maximum time (in seconds) a single collect_data execution is allowed to run
# before yielding to the next scheduled interval. Checkpoint is saved after each
# page, so the next run resumes where this one stopped.
MAX_EXECUTION_TIME = 300  # 5 minutes
# Maximum query time window (in seconds) for a single execution. If the gap
# between start_date and end_date exceeds this value, end_date is capped so that
# each run processes a bounded amount of data.
MAX_QUERY_WINDOW_SECONDS = 86400  # 24 hours
# Maximum number of consecutive non-200 responses (e.g. 401 re-auth, 403
# rate-limit) tolerated inside a single get_*_events call before giving up.
# Prevents silent infinite retry loops that manifest as ingestion stalls.
MAX_RETRIES_ON_ERROR = 10
