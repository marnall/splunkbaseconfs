##
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

# GitHub Constants
GITHUB_ORGANIZATION = "orgs"
GITHUB_ENTERPRISE = "enterprises"
GITHUB_CS_ALERT_SOURCE_TYPE = "github:cloud:code:scanning:alerts"
GITHUB_DB_ALERT_SOURCE_TYPE = "github:cloud:dependabot:scanning:alerts"
GITHUB_SS_ALERT_SOURCE_TYPE = "github:cloud:secret:scanning:alerts"

GITHUB_AUDIT_LOG_SOURCE_TYPE = "github:cloud:audit"
GITHUB_USER_SOURCE_TYPE = "github:cloud:user"
DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
UCC_EXECPTION_EXE_LABEL = "splunk_ta_github_exception_{}"

# GitHub Endpoints
GITHUB_ALERTS_ENDPOINT = "https://api.github.com/{}/{}/{}/alerts"

GITHUB_AUDIT_LOG_ENDPOINT = "https://api.github.com/{}/{}/audit-log"

API_ALERT_TYPE = {
    "code_scanning_alerts": "code-scanning",
    "dependabot_alerts": "dependabot",
    "secret_scanning_alerts": "secret-scanning",
}

ALERT_TYPE_MESSAGES = {
    "code_scanning_alerts": "Code Scanning",
    "dependabot_alerts": "Dependabot Scanning",
    "secret_scanning_alerts": "Secret Scanning",
}
