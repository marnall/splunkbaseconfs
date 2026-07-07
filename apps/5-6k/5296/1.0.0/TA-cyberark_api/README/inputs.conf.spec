[cyberark_api_safes://<name>]
global_account = 
logon_endpoint_url = https://<IIS_Server_Ip>/PasswordVault/API/auth/LDAP/Logon
safes_endpoint_url = Members of the Safe. The user performing this task must have ViewSafeMembers permissions in the Safe.

[cyberark_api_accounts://<name>]
global_account = 
logon_endpoint_url = 
accounts_endpoint_url = 

[cyberark_session_recordings://<name>]
global_account = 
logon_endpoint_url = https://<IIS_Server_Ip>/PasswordVault/API/auth/LDAP/Logon
recording_endpoint_url = Endpoint - Recordings of PSM, PSM for SSH, or OPM sessions.
fromtime = From time filter, used only as initial starting point, the addon start from check point after first run. Checkpoint is created on each addon run. Format:YYYY-MM-DDTHH:MM:SS