##
## SPDX-FileCopyrightText: 2025 Splunk LLC
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[<name>]
domain = The Okta domain name for the account (yourdomain.okta.com)
password = The API Token for this account (encrypted) -- https://developer.okta.com/docs/api/getting_started/getting_a_token.html
auth_type = Authentication type of the account - Basic or OAuth2
client_id = Client ID of the Okta Web App
client_secret = Client Secret of the Okta Web App (encrypted)
client_id_oauth_credentials = Client ID of the Okta Client-Credentials grant type
client_secret_oauth_credentials = Client Secret of the Okta Client-Credentials grant type (encrypted)
redirect_url = Redirect URL which should be pasted in Okta Web App's redirect sign-in url section
endpoint = Okta domain endpoint
endpoint_url = Okta domain endpoint_url for Client-Credentials grant type
access_token = Access Token obtained from OAuth2 workflow (encrypted)
refresh_token = Refresh Token obtained from OAuth2 workflow (encrypted)
scope = Scopes that are requested by the TA to get the Access Token & Refresh Token
