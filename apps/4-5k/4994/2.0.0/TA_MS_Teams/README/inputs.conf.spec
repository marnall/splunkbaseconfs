[teams_call_records://<name>]
endpoint = Default: v1.0
environment = Default: public
exclude_null_values = Default: True
global_account = 
index = Default: default
interval = Time interval of input in seconds.
start_date = The date/time to start collecting data.  If no value is give, the input will start getting data 7 days in the past.
tenant_id = 

[teams_user_report://<name>]
environment = Default: public
global_account = 
index = Default: default
interval = Time interval of input in seconds.
period = Default: D30
tenant_id = 

[teams_webhook://<name>]
cert_file = The path to the SSL certificate file (if you want to use encryption); typically uses .DER, .PEM, .CRT, .CER file extensions
index = Default: default
interval = Time interval of input in seconds.
key_file = The path to the SSL certificate key file (if the certificate requires a key); typically uses .KEY file extension
webhook_path = A wildcard that the path of requests must match (paths generally begin with a "/" and can include a wildcard)
webhook_port = Port for the webhook

[teams_subscription://<name>]
endpoint = Default: v1.0
environment = Default: public
global_account = 
index = Default: default
interval = Time interval of input in seconds.
tenant_id = 
webhook_url = 

[teams_call_record://<name>]
endpoint = Default: v1.0
environment = Default: public
global_account = 
index = Default: default
interval = Time interval of input in seconds.
max_batch_size = Specify the maximum number of call records retrieved per interval.  Default: 5000
tenant_id = 
