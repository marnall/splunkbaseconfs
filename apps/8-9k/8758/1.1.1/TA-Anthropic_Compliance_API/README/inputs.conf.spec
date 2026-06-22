[anthropic_activity_feed_input://<name>]
account = Account to use. Supports both Compliance Access Keys (sk-ant-api01-...) and Admin Keys (sk-ant-admin01-...). Required scope: read:compliance_activities.
index = (Default: default)
interval = How often to poll the Activity Feed, in seconds. (Default: 300)
lookback_hours = Number of hours to look back on the first run (default: 168 = 7 days). Subsequent runs use checkpointing. (Default: 168)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[anthropic_org_users_input://<name>]
account = Account to use. Requires a Compliance Access Key (sk-ant-api01-...) with scopes: read:compliance_org_data, read:compliance_user_data. Admin Keys will fail with 401.
fetch_groups = When enabled, fetches groups and their members via /v1/compliance/groups. Requires read:compliance_org_data and read:compliance_user_data scopes.
fetch_org_roles = When enabled, fetches roles for each organization via /v1/compliance/organizations/{uuid}/roles. Requires read:compliance_org_data scope.
index = (Default: default)
interval = How often to refresh the org users list, in seconds. (Default: 3600)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[anthropic_apps_input://<name>]
account = Account to use. Requires a Compliance Access Key (sk-ant-api01-...) with scope: read:compliance_user_data. Admin Keys will fail with 401.
fetch_project_attachments = When enabled, fetches attachments for each project via /v1/compliance/apps/projects/{id}/attachments. Increases API call volume significantly.
index = (Default: default)
interval = How often to poll projects, in seconds. (Default: 3600)
lookback_hours = Number of hours to look back on the first run (default: 168 = 7 days). Subsequent runs use checkpointing. (Default: 168)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set

[anthropic_chats_input://<name>]
account = Account to use. Requires a Compliance Access Key (sk-ant-api01-...) with scopes: read:compliance_org_data, read:compliance_user_data. Admin Keys will fail with 401.
fetch_chat_messages = When enabled, for every chat seen, also fetches the full message thread via /v1/compliance/apps/chats/{id}/messages and emits one event per message under sourcetype anthropic:compliance:apps:chat_message. Doubles or more API call volume; off by default.
index = (Default: default)
interval = How often to poll chats, in seconds. Default 14400 (4h). (Default: 14400)
lookback_hours = Number of hours to look back on the first run (default: 168 = 7 days). Subsequent runs use checkpointing on the newest updated_at seen. (Default: 168)
python.required = {3.7|3.9|3.13}
* For Python scripts only, selects which Python version to use.
* Set to "3.9" to use the Python 3.9 version.
* Set to "3.13" to use the Python 3.13 version.
* Optional.
* Default: not set
