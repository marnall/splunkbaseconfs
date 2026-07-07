[ga://default]
*This is how the Google Workspaces For Splunk is configured

credential = <value>
*This is the domain name for the Google Workspaces Domain

input_name = <value>
* This is a user readable name

application_name = <value>
*This is the service name to pull from the Google APIs. Refer to the README for specifics.

lookback = <value>
*Allows for extra configuration for the API Calls.

guid = <value>
* The singluar guid for reference

[ga_user://default]
*This is how the Google Workspaces For Splunk is configured

credential = <value>
*This is the domain name for the Google Workspaces Domain

input_name = <value>
* This is a user readable name

application_name = <value>
*This is the service name to pull from the Google APIs. Refer to the README for specifics.

lookback = <value>
*Allows for extra configuration for the API Calls.

guid = <value>
* The singluar guid for reference

user_key = <value>
* The user key to pull data for

[ga_usage://default]
*This is how the Google Workspaces For Splunk is configured

credential = <value>
*This is the domain name for the Google Workspaces Domain

application_name = <value>
*This is the service name to pull from the Google APIs. Refer to the README for specifics.

input_name = <value>
* This is a user readable name

email_forward_check = <bool>
* Should the email forwarding settings be enriched.

lookback = <value>
*Allows for extra configuration for the API Calls.

guid = <value>
* The singluar guid for reference

[ga_alerts://default]
*This is how the Google Workspaces For Splunk is configured

credential = <value>
*This is the domain name for the Google Workspaces Domain

src = <value>
*This is the source to pull from the Google APIs. Refer to the README for specifics.

input_name = <value>
* This is a user readable name

lookback = <value>
*Allows for extra configuration for the API Calls.

guid = <value>
* The singluar guid for reference

[ga_classroom://default]
* Consume Classroom Data

course_ids = <value>
* The specific courses to pull

credential = <value>
* The credential to use

guid = <value>
* The specific GUID
input_name = <value>
* Friendly name
lookback = <value>
* How far back in days
servicename = <value>
* What service to pull

write_courses = <boolean>
* Should we write out the course information?

[ga_bigquery://default]
* Query BigQuery Tables

project = <value>
* This is the project ID for the big query table

table = <value>
* This is the table name to query in the form <dataset>.<table>

dataset = <value>
* The dataset to query with.

credential = <value>
* The credential to use

start_row = <value>
* The row number to start at.

max_rows = <value>
* The max number of messages to pull per interval

ingest_type = <value>
* Either "row" or "time" or "query" for style of ingest from table

enriched_pasta = <value>
* Additional information specific to the ingest type.

guid = <value>
* Input GUID

input_name = <value>
* Friendly Name

[ga_pubsub://default]
* Subscribe to PubSub

project = <value>
* This is the project ID for the pubsub

subscription = <value>
* This is the subscription ID for the pubsub

credential = <value>
* The credential to use

guid = <value>
* Input GUID

max_messages = <value>
* Max number to pull at a time. Default: 1M

input_name = <value>
* Friendly Name

[ga_ss://default]
*This is how the ss sync is configured
guid = <value>
* Input GUID

input_name = <value>
* Friendly Name

ss_id = <value>
*This is the SpreadSheet ID to sync

ss_sheet = <value>
* This is the sheet id to sync

credential = <value>
* The credential to use

destination = <value>
* Where should we put this? Defaults to index. Values: index, kvstore, transform

[ga_forms://default]
*This is how the forms sync is configured

guid = <value>
* Input GUID

input_name = <value>
* Friendly Name

form_id = <value>
*This is the Form ID to sync

use_check = <value>
* This is flag to use checkpoint in response gathering
credential = <value>
* The credential to use

destination = <value>
* Where should we put this? Defaults to index. Values: index, kvstore, transform

[ga_analytics://default]
*This is how the ss sync is configured
guid = <value>
* Input GUID

input_name = <value>
* Friendly Name

view = <value>
* This is the Google Analytics View to consume data from

metrics = <value>
*This is the Metrics to consume

dimensions = <value>
* This is the dimensions to consume

time_field = <value>
* This is the field from the data to use as the event time

backfill = <value>
* This is the number of days to backfill

accountId = <value>
* (Optional) Set via front end to populate accountId in events

webPropertyId = <value>
* (Optional) Set via front end to populate webPropertyId in events

websiteUrl = <value>
* (Optional) Set via front end to populate websiteURL in events

timeZone = <value>
* (Optional) The Profile Timezone as set in Google Analytics

credential = <value>
* The credential to use