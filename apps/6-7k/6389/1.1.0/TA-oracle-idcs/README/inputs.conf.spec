[cisco_idcs://<name>]
your_cisco_idcs_url = without "/" at the end of the URLeg:- https://idcs-xxxx.identity.oraclecloud.com
oauth_2_client_id = 
oauth_2_client_secret = 
polling_interval = in minutes. Eg:- 60
oauth_2_grant_type = Only Supports refresh_token now
update_existing_tokens = Select YES if you are setting up the addon for the first time and want the addon to use the access token and refresh token value provided.
oauth_2_access_token = 
oauth_2_refresh_token = 
oauth_2_token_refresh_url = 
initial_pull_flag = Enable one time pull from an earlier date time. If enabled, the addon will attempt to pull logs from a specified time only for one time and continue pulling logs according to the polling interval.
initial_pull_time = Format : 2022-04-03T06:14:45.191Z