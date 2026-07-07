[issues_input://<name>]
wiz_account =
severity =
project_id = Please Enter Project ID (Keep it blank for getting data of all projects)
sync_frequency = Enter the frequency of full sync in days. Enter 0 if you don't want full syncs
include_security_categories = Tick this box if you want to include security categories info in the issues payload
re_assessed_issues = Tick this box if you want to pull re-assessed Issues incrementally
request_timeout = HTTP read timeout (seconds) for Wiz API calls. Default 180. Bump for cross-region or large-tenant deployments where pages legitimately take longer.

[user_audit_logs://<name>]
wiz_account =
historical_polling_days = Historical Polling Days value should be in range of 1-180
window_multiplier = Cap on per-poll audit window expressed as multiples of `interval`. Range 1-1440. Each poll fetches at most `interval * window_multiplier` seconds of audit events; bounded windows guarantee the cursor advances even when a busy tenant's backlog cannot finish paginating in one run. Default 60 (with default interval=60s → 1-hour windows). Raise to widen each window for faster back-fill on quiet tenants; lower for very busy tenants.
request_timeout = HTTP read timeout (seconds) for Wiz API calls. Default 180. Bump for cross-region or large-tenant deployments where pages legitimately take longer.

[vulnerabilities_input://<name>]
wiz_account =
severity =
asset_type =
project_id = Please Enter Project ID (Keep it blank for getting data of all projects)
sync_frequency = Enter the frequency of full sync in days. Enter 0 if you don't want full syncs
related_issue_severity = Enter the severities of related issue. Leave empty for all severities.
daily_update_by = Select how daily updates should be determined
request_timeout = HTTP read timeout (seconds) for Wiz API calls. Default 180. Bump for cross-region or large-tenant deployments where pages legitimately take longer.

[detections_input://<name>]
wiz_account =
severity =
project_id = Please Enter Project ID (Keep it blank for getting data of all projects)
historical_polling_days = Historical Polling Days value should be in range of 1-90
include_triggering_events = Tick this box if you want to include the list of triggering events in the detections payload
request_timeout = HTTP read timeout (seconds) for Wiz API calls. Default 180. Bump for cross-region or large-tenant deployments where pages legitimately take longer.
