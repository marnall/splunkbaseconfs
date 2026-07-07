##
## SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[google_cloud_pubsub://<name>]
google_credentials_name = stanza name in google_credentials.conf
google_project = The project ID
google_subscriptions = List of subscriptions' names

[google_cloud_monitor://<name>]
placeholder = <value>
google_monitored_projects = The monitored projects

[google_cloud_billing://<name>]
placeholder = <value>

[google_cloud_bucket_metadata://<name>]
google_credentials_name = stanza name in google_credentials.conf
google_project = the project name
bucket_name = bucket name
chunk_size = size of a chunk in bytes while downloading blob content
index =
interval =
number_of_threads = The number of threads that will work concurrently to fetch files from bucket and ingest it into Splunk
conf_version = Indicates the config version

[google_cloud_resource_metadata://<name>]
placeholder = <value>

[google_cloud_resource_metadata_cloud_storage://<name>]
placeholder = <value>

[google_cloud_resource_metadata_vpc_access://<name>]
placeholder = <value>

[google_cloud_resource_metadata_kubernetes://<name>]
placeholder = <value>

[google_cloud_pubsub_lite://<name>]
google_credentials_name = stanza name in google_credentials.conf
google_project = google pubsub project ID
location = select the topic i.e.regional or zonal
pubsublite_regions = select the supported regions for pubsub lite service
pubsublite_zones = select the supported zones for pubsub lite service
pubsublite_subscriptions = List of pubsub lite subscriptions names
index = splunk index
sourcetype = splunk sourcetype name.
number_of_threads = Count to indicate how many thread workers will work in parallel to fetch data from pubsublite and ingest it into Splunk
messages_outstanding = Count of after how many max messages, TA will pause receiving messages if we have not acknowledged 1st message.
bytes_outstanding = Count of after how much Megabyte, TA will pause receiving messages if we have not acknowledged 1st message.

[google_cloud_pubsub_based_bucket://<name>]
google_credentials_name = stanza name in google_credentials.conf
google_project = the project name
google_subscriptions = google pubsub subscription name
index = splunk index
sourcetype = splunk sourcetype name.
message_batch_size = number of messages to receive in batch
number_of_threads = The number of threads that will work in parallel to fetch data and ingest it into Splunk
