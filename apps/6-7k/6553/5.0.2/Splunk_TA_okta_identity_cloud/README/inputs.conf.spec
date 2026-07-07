##
## SPDX-FileCopyrightText: 2025 Splunk LLC
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[okta_identity_cloud://<name>]
interval = Interval in seconds. The input will be triggered at every interval amount of time and fetch the data.
index = Index name. Index to which you want to send data. It refers to index name in indexes.conf.
metric = The metric (data type) you wish to collect the data for
global_account = Select the Okta Account from the list which you want to collect the events.
logs_delay = Delay in Seconds while live data collection for logs metric to avoid data loss.
query_window_size = Difference between the start and end times for each API call (seconds).
start_date = Start Date for starting data collection
end_date = End Date for ending the data collection
use_existing_checkpoint = To modify the start date in Edit mode, click on "No" option of this radio button. By selecting "No", it will delete the existing checkpoint and start data collection from the provided Start Date
collect_uris = For Apps metric, if user wants to ingest URIs of not. By default, the URIs are ingested in event
fetch_stats = For Groups metric, if user wants to ingest statastical data about Groups or not. The stats are ingested in the event
