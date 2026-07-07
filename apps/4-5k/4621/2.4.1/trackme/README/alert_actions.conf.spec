
[trackme_auto_ack]
python.version = python3
python.required = <comma-separated list>
param.ack_period = <string> Ack period (seconds). It's a required parameter. It's default value is 86400.
param.ack_type = <string> Ack type. It's a required parameter. It's default value is unsticky.

[trackme_free_style_rest_call]
python.version = python3
python.required = <comma-separated list>
param.endpoint_url = <string> TrackMe Endpoint URL. It's a required parameter.
param.http_mode = <list> HTTP mode. It's a required parameter. It's default value is get.
param.http_body = <string> HTTP body.

[trackme_notable]
python.version = python3
python.required = <comma-separated list>
param.title = <string> The notable event title.
param.drilldown_root_uri = <string> This value is used to build the drilldown link in the notable event and fhe entity triggering, This should be the base URL for Splunk Web.
param.drilldown_earliest = <string> This value is used to build the drilldown link in the notable event and fhe entity triggering, This should be the earliest time for the drilldown link.

[trackme_stateful_alert]
python.version = python3
python.required = <comma-separated list>
param.delivery_target = <list> Delivery target (Emails, Ingest, etc). It's a required parameter. It's default value is 0.
param.environment_name = <string> The environment name to use in the email content header, defaults to Splunk. Define it as the fully qualified address of the environment so it appears as a valid link in the email, example: https://splunk.example.com
param.email_account = <list> Email account.
param.email_recipients = <string> Recipients.
param.email_send_update_if_ack_active = <list> Send update notification if Ack is active. It's default value is 0.
param.orange_as_alerting_state = <list> Consider orange as in alerting state. It's a required parameter. It's default value is 0.
param.generate_charts = <string> Include charts generation in the email.  It's default value is 1.
param.theme_charts = <string> Charts theme. It's a required parameter. It's default value is dark.
param.timerange_charts = <string> Charts time window. It's default value is 24h.
param.drilldown_root_uri = <string> Splunk root uri.
param.commands_mode = <list> Commands mode.  It's default value is streaming.
param.commands_opened = <string> Command for new incidents.
param.commands_updated = <string> Command for updated incidents.
param.commands_closed = <string> Command for closed incidents.
param.auto_ack_enabled = <list> Auto ack enabled. It's default value is 1.
param.auto_ack_period = <string> Auto ack period. It's default value is 86400.
param.auto_ack_type = <string> Auto ack type. It's default value is sticky.
param.priority_levels_emails = <string> Priority levels selection for email notifications, you can restrict the scope of email notifications to a specific list of priority levels.
param.priority_levels_commands = <string> Priority levels selection for commands execution, you can restrict the scope of commands execution to a specific list of priority levels.
param.ai_status_report = <list> Enable AI status report generation. It's default value is 0.
param.ai_provider_name = <string> The AI provider name to use for AI status report generation.