# Copyright (C) 2005-2016 Splunk Inc. All Rights Reserved.
# The file contains the specification for database identities (username/password)

[<name>]

username = <string>
# required
# the username for this database connection identity

password = <string>
# required
# The encrypted value of the password for this database connection identity.

token = <string>
# optional
# The encrypted value of the token for this database connection identity.

domain_name = <string>
# optional
# Specifies the windows domain name which the username belongs to

use_win_auth =  [true|false]
# optional
# Specifies whether the Windows Authentication Domain is used

identity_type =  [normal|cyberark|hashicorp|token]
# optional
# Specifies type of the identity
# normal is the default type
# normal - username and password provided by user
# cyberark - password is fetched from CyberArk Vault
# hashicorp - password is fetched from HashiCorp Vault
# token - token is used for authentication

protocol_type =  [http|https]
# optional
# Specifies type of the connection to CyberArk
# http is the default type
# http - unsecure connection to a CyberArk
# https - secure connection, certificate is required

appId = <string>
# optional
# required when identity_type = cyberark
# Specifies Application ID needed to get credentials from the CyberArk

safe = <string>
# optional
# required when identity_type = cyberark
# Specifies Safe in the CyberArk where the password is saved

object = <string>
# optional
# required when identity_type = cyberark
# Specifies object name in the CyberArk where the password is saved

url = <string>
# optional
# required when identity_type = cyberark
# Domain where CyberArk Central Credential Provider is hosted

port = <integer>
# optional
# required when identity_type = cyberark
# Port where CyberArk Central Credential Provider is available

certificate = <string>
# optional
# required when identity_type = cyberark and protocol_type = https
# The encrypted value of the certificate for this CyberArk connection.

hashicorp_namespace = <string>
# HashiCorp Namespace
# Required when identity_type = hashicorp and uses HashiCorp Enterprise with namespace.

hashicorp_secrets_engine = [KEY_VALUE_V1|KEY_VALUE_V2|DATABASES]
# HashiCorp Secrets Engine
# Required when identity_type = hashicorp

hashicorp_secrets_engine_path = <string>
# HashiCorp Secrets Engine Path
# Required when identity_type = hashicorp

hashicorp_secret_path = <string>
# HashiCorp Secrets Path
# Required when identity_type = hashicorp and hashicorp_secrets_engine = KEY_VALUE_V1 or KEY_VALUE_V2

hashicorp_key_name = <string>
# HashiCorp Key Name
# Required when identity_type = hashicorp and hashicorp_secrets_engine = KEY_VALUE_V1 or KEY_VALUE_V2

hashicorp_role_name = <string>
# HashiCorp Role Name
# Required when identity_type = hashicorp and hashicorp_secrets_engine = DATABASES

hashicorp_auth_method_path = <string>
# HashiCorp Auth Method Path
# Required when identity_type = hashicorp

hashicorp_role_id = <string>
# HashiCorp Role Id
# Required when identity_type = hashicorp

hashicorp_secret_id = <string>
# HashiCorp Secret Id
# Required when identity_type = hashicorp

sync_frequency = <integer|string>
# Synchronization Frequency
# Optional
# How often the password is sync from HashiCorp or CyberArk

oauth2_client_id = <string>
# Client ID
# Required when identity_type = oauth2

oauth2_client_secret = <string>
# Client Secret
# Required when identity_type = oauth2

oauth2_account_url = <string>
# Account URL
# Required when identity_type = oauth2

oauth2_redirect_url = <string>
# Redirect URL
# Required when identity_type = oauth2

oauth2_refresh_token = <string>
# Refresh Token
# Required when identity_type = oauth2

oauth2_access_token = <string>
# Access Token
# Required when identity_type = oauth2

oauth2_access_token_expires_at = <string>
# Expiration Time of Access Token
# Required when identity_type = oauth2

oauth2_identity_provider = [SNOWFLAKE]
# Identity Provider (IdP)
# Required when identity_type = oauth2
