[test_metrics_stream://<name>]
cea_tests = Select CEA Tests
endpoint_tests = Select Endpoint Tests
hec_target = HEC Target URL.
hec_token = HEC Token created for Webhook URL.
thousandeyes_stream_id = ThousandEyes Stream ID for given Input
interval = Interval to fetch the Network Path Data from API, in seconds.  Default: 300
index = Default: default
related_paths = Check the checkbox if you want to collect Network Path Data.
test_index = Index to collect Tests data from stream
thousandeyes_acc_group = Select Account Group
thousandeyes_user = ThousandEyes User to use for this input.
tags = Tags to filter the test to be streamed.

[test_traces_stream://<name>]
cea_tests = Select CEA Tests for trace collection (page-load and web-transactions only)
hec_target = HEC Target URL.
hec_token = HEC Token created for Webhook URL.
thousandeyes_stream_id = ThousandEyes Stream ID for given Input
test_index = Index to collect Trace data from stream
thousandeyes_acc_group = Select Account Group
thousandeyes_user = ThousandEyes User to use for this input.
tags = Tags to filter the test to be streamed.

[event://<name>]
index = Default: default
interval = Time interval of the data input, in seconds.  Default: 300
thousandeyes_acc_group = Select Account Group
thousandeyes_user = ThousandEyes User to use for this input.

[activity_logs_stream://<name>]
hec_target = HEC Target URL.
hec_token = HEC Token created for Webhook URL.
thousandeyes_stream_id = ThousandEyes Stream ID for given Input
activity_index = Index to collect Activity Logs data from stream
thousandeyes_acc_group = Select Account Group
thousandeyes_user = ThousandEyes User to use for this input.

[thousandeyes_refresh_tokens://<name>]
index = Default: default
interval = Time interval of the data input, in seconds. Default: 604800 (1 week)
account_refresh_sleep_interval = Sleep interval between account refreshes. Default: 60 (1 min)
dry_run = Test mode - log actions without making changes. Default: false
disabled = on/off input. Default: false

[alerts_stream://<name>]
alert_rules = Select Alert Rules to monitor
hec_target = HEC Target URL.
hec_token = HEC Token created for Webhook URL.
alerts_index = Index to collect Alerts data from webhooks
thousandeyes_acc_group = Select Account Group
thousandeyes_user = ThousandEyes User to use for this input.
webhook_operation_id = Auto-generated webhook operation ID (internal use)
webhook_connector_id = Auto-generated webhook connector ID (internal use)