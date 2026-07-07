[activity_report://<name>]
account = Service account to use for this input.
application = (Default: admin)
index = Index where data is going to be ingested. (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)
lookbackOffset = A lookback offset, in seconds, from current time to account for data lag. (Default: 1800)

[gws_gmail_logs://<name>]
account = Service account to use for this input.
dataset_location = BigQuery dataset location name. (Default: US)
dataset_name = BigQuery dataset name. (Default: gmail_logs_dataset)
gcp_project_id = GCP project where you have BigQuery data.
index = Index where data is going to be ingested. (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)

[gws_gmail_logs_migrated://<name>]
account = Service account to use for this input.
dataset_location = BigQuery dataset location name. (Default: US)
dataset_name = BigQuery dataset name.
gcp_project_id = GCP project where you have BigQuery data.
index = Index where data is going to be ingested. (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)
table_name = BigQuery table name. (Default: activity)

[gws_user_identity://<name>]
account = Service account to use for this input.
gws_customer_id = GWS Customer ID that will be used for the identity list.
gws_view_type = GWS view type (Default: domain_public)
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 21600)

[gws_alert_center://<name>]
account = Service account to use for this input.
alert_source = Google Workspace alert source.
index = (Default: default)
interval = Time interval of the data input, in seconds. (Default: 300)

[gws_usage_report://<name>]
account = Service account to use for this input.
endpoint = Type endpoint from which reports will be collected (Default: user)
index = (Default: default)
interval = Schedule of the data input, in cron format. (Default: 34 1 * * *)
start_date = Start date for data collection in UTC timezone. Default: 30 days ago in UTC. Format: YYYY-MM-DD
