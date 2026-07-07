[obsidian_audit://<name>]
obsidian_api_url = Select the option that best aligns with your organization's current location.
api_token = An API Token can be obtained from <your tenant>.obsec.io/settings?tab=api-access-tokens
subdomain = Enter the tenant subdomain (acme if full url is acme.obsec.io)
proxy_setting = If set to a valid proxy, Obsidian will use this to make outbound connections.

[obsidian_posture_rules://<name>]
obsidian_api_url = Select the option that best aligns with your organization's current location.
api_token = An API Token can be obtained from <your tenant>.obsec.io/settings?tab=api-access-tokens
subdomain = Enter the tenant subdomain (acme if full url is acme.obsec.io)
proxy_setting = If set to a valid proxy, Obsidian will use this to make outbound connections.

[obsidian_posture_violations://<name>]
obsidian_api_url = Select the option that best aligns with your organization's current location.
api_token = An API Token can be obtained from <your tenant>.obsec.io/settings?tab=api-access-tokens
subdomain = Enter the tenant subdomain (acme if full url is acme.obsec.io)
proxy_setting = If set to a valid proxy, Obsidian will use this to make outbound connections.

[obsidian_posture_settings://<name>]
obsidian_api_url = Select the option that best aligns with your organization's current location.
api_token = An API Token can be obtained from <your tenant>.obsec.io/settings?tab=api-access-tokens
subdomain = Enter the tenant subdomain (acme if full url is acme.obsec.io)
proxy_setting = If set to a valid proxy, Obsidian will use this to make outbound connections.

[obsidian_events://<name>]
obsidian_api_url = Select the option that best aligns with your organization's current location.
api_token = An API Token can be obtained from <your tenant>.obsec.io/settings?tab=api-access-tokens
subdomain = Enter the tenant subdomain (acme if full url is acme.obsec.io)
event_query = "service:microsoft" (no quotes) to receive only Microsoft events
time_window_seconds = Default time window in seconds for event fetching (default:7200, min:1800)
min_time_window_seconds = Minimum time window in seconds for event fetching (default:60, min:2)
batch_size = Batch size for processing (default:500, min:100, max:5000)
eps_threshold = EPS threshold for throttling adjustments (default:100, min:50)
proxy_setting = If set to a valid proxy, Obsidian will use this to make outbound connections.

[obsidian_alerts://<name>]
obsidian_api_url = Select the option that best aligns with your organization's current location.
api_token = An API Token can be obtained from <your tenant>.obsec.io/settings?tab=api-access-tokens
subdomain = Enter the tenant subdomain (acme if full url is acme.obsec.io)
alert_query = "service:microsoft" (no quotes) to receive only Microsoft alerts
fetch_related_events = Fetch the event bodies related to the alerts that are fetched.
max_retries = This will only work when you checked 'Fetched Related Events'. Default value is 5.
initial_alert_id = This is optional for customers who couldn't upgrade the app and need to reinstall and reconfigure the modular input. It helps prevent re-indexing of existing alerts.
proxy_setting = If set to a valid proxy, Obsidian will use this to make outbound connections.

[obsidian_identity_alerts://<name>]
obsidian_api_url = Select the option that best aligns with your organization's current location.
api_token = An API Token can be obtained from <your tenant>.obsec.io/settings?tab=api-access-tokens
subdomain = Enter the tenant subdomain (acme if full url is acme.obsec.io)
confidence = Select the confidence score of alert triage by identity
date_range = Select the date range for the alert triage by identity
show_resolved_alerts = If show identities with all alerts resolved
proxy_setting = If set to a valid proxy, Obsidian will use this to make outbound connections.