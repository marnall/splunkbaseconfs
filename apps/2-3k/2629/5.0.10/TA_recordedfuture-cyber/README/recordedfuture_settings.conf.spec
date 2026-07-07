[proxy]
proxy_enabled = <bool>
proxy_type = <string>
proxy_url = <string>
proxy_port = <integer>
proxy_username = <string>
proxy_rdns = <bool>

[logging]
loglevel = <string>

[settings]
api_key = <string>
recorded_future_api_url = <string>
verify_ssl = <bool>

[risk_list://<name>]
category = <string>
interval = <integer>
fusion_file = <string>
enabled = <bool>

[alert://<name>]
alert_status = <string>
triggered = <string>
alert_rule_id = <string>
alert_rule_name = <string>
enabled = <bool>
limit = <integer>