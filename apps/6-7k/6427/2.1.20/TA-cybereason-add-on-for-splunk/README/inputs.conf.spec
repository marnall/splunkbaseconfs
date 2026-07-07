[malicious_data_input://<name>]
base_url = The base URL to Cybereason Server (without https://)
username = The username for Cybereason Account
password = The password for Cybereason Account
hist_days = The number of days to fetch Historical data in the first poll
buffer_time = Time for which data to be cached(seconds)
authentication_type = The type of authentication to be used
group_name = The Group name for Cybereason Sensors Group
ssl_certificate_path = Absolute Path to 3rd-Party Signed Non-Default Certificates to be used for SSL Verification at the time of data polling. If not provided, the default internal certificates will be used.
malops = MalOps Endpoint, Enable this to fetch the MalOps
suspicious_objects = Suspicious Objects Endpoint, Enable this to fetch the Suspicious Objects
malware = Malware Endpoint, Enable this to fetch the Malware
pull_comments = Pull Malops with Latest Comments only
select_malop_status = Malop Status, Select the status for which you want to fetch Malops

[user_activity_input://<name>]
base_url = The base URL to Cybereason Server (without https://)
username = The username for Cybereason Account
password = The password for Cybereason Account
hist_days = The number of days to fetch Historical data in the first poll
authentication_type = The type of authentication to be used
ssl_certificate_path = Absolute Path to 3rd-Party Signed Non-Default Certificates to be used for SSL Verification at the time of data polling. If not provided, the default internal certificates will be used.
users = Users Endpoint, Enable this to fetch the Users
user_action_logs = User Action Logs Endpoint, Enable this to fetch the User Action Logs
logon_sessions = Logon Sessions Endpoint, Enable this to fetch the Logon Sessions
