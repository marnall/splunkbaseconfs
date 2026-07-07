##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[<name>]
username = Username for basic authentication
password = Encrypted password for basic authentication
token = Encrypted security token for the user
auth_type = Account auth type (oauth_client_credentials/oauth/basic)
endpoint = Salesforce endpoint value for oauth
client_id = App's client id for authorization code flow
client_secret = Encrypted app's client secret for authorization code flow
client_id_oauth_credentials = App's client id for oauth client credentials flow
client_secret_oauth_credentials = Encrypted app's client secret for oauth client credentials flow
sfdc_api_version = Salesforce API version (42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0, 49.0, 50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0, 59.0, 60.0, 61.0, 62.0, 63.0, 64.0)
is_migrated = Whether account with old oauth client credentials has been migrated or not (for > v5.1.0).
