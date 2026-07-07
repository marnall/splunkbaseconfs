##
## SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[inventory_sync_service://<name>]
search_head_address = <string> Splunk search head instance host
search_head_port = <integer> Splunk search head instance port
search_head_username = <string> Splunk search head instance user name
search_head_password = <string> Splunk search head instance user password
use_failover_search_head = <bool> Use another Splunk search head instance as failover
failover_search_head_address = <string> Failover Splunk search head instance host
failover_search_head_port = <integer> Failover Splunk search head instance port
failover_search_head_username = <string> Failover Splunk search head instance user name
failover_search_head_password = <string> Failover Splunk search head instance user password
interval = <integer> Sync interval in seconds
run_only_one = <bool> set in defaults, must always be false to make sure at Victoria stack that one input instance is running at each SH
start_by_shell = <bool> set in defaults, must always be false to make sure that modinput process is not wrapped into a shell. Wrapping into a shell on some OSs prevents input process form shutting down when it's disabled

[device_api_inventory_sync_service://<name>]
api_client_id = <string> OAuth2 API Client ID, provided by CrowdStrike
api_client_secret = <string> OAuth2 API Client secret, provided by CrowdStrike
api_base_url = <string> Points to CrowdStrike API gateway, usually it's https://api.crowdstrike.com
interval = <integer> Sync interval in seconds, i.e. how often service requests CrowdStrike device API to check for updated devices
run_only_one = <bool> set in defaults, must always be true to make sure at Victoria stack that only input instance is running at SHC
start_by_shell = <bool> set in defaults, must always be false to make sure that modinput process is not wrapped into a shell. Wrapping into a shell on some OSs prevents input process form shutting down when it's disabled

[fdr_s3bucket_monitor_service://<name>]
aws_bucket = <string> FDR AWS S3 bucket
aws_collection = <string> Name of an FDR AWS collection defined in splunk_ta_crowdstrike_fdr_aws_collections.conf
interval = <integer> Bucket check interval
run_only_one = <bool> set in defaults, must always be true to make sure at Victoria stack that only one input instance is running at SHC
start_by_shell = <bool> set in defaults, must always be false to make sure that modinput process is not wrapped into a shell. Wrapping into a shell on some OSs prevents input process form shutting down when it's disabled

[simple_consumer_input://<name>]
aws_sqs_url = <string> AWS SQS queue URL
aws_sqs_ignore_before  = <string> datetime in form of YYYY-MM-DD HH:MM marking max age of SQS messages to be processed
aws_sqs_visibility_timeout = <integer> AWS SQS queue visibility timeout in seconds
aws_collection = <string> Name of an FDR AWS collection defined in splunk_ta_crowdstrike_fdr_aws_collections.conf
cs_event_encoding = <string> Encoding of the events stored at CrowdStrike feed, in most cases it's utf-8
cs_ithr_type = <string> Defines which host resolution method to use if any. Values "inventory", "device_api" or no value are supported.
cs_event_filter_name = <string> Name of a CrowdStrike event filter defined in splunk_ta_crowdstrike_fdr_cs_event_filters.conf
cs_device_field_filter_name = <string> Name of a CrowdStrike device field event filter defined in splunk_ta_crowdstrike_fdr_cs_device_field_filter.conf
collect_external_events = <bool> 1 to collect external  security  events, otherwise 0
index_for_external_events = <string> optional separate index to store external security events
collect_ztha_events = <bool> 1 to collect zero trust host accessment  security  events, otherwise 0
index_for_ztha_events = <string> optional separate index to store zero trust host assessment security events
collect_inventory_aidmaster = <bool> 1 to collect aidmaster inventory events, otherwise 0
index_for_aidmaster_events = <string> optional separate index to store aidmaster inventory events
collect_inventory_managedassets = <bool> 1 to collect managedassets inventory events, otherwise 0
index_for_managedassets_events = <string> optional separate index to store managedassets inventory events
collect_inventory_notmanaged = <bool> 1 to collect notmanaged inventory events, otherwise 0
index_for_notmanaged_events = <string> optional separate index to store notmanaged inventory events
collect_inventory_appinfo = <bool> 1 to collect appinfo inventory events, otherwise 0
index_for_appinfo_events = <string> optional separate index to store appinfo inventory events
collect_inventory_userinfo = <bool> 1 to collect userinfo inventory events, otherwise 0
index_for_userinfo_events = <string> optional separate index to store userinfo inventory events
index = <string>  Splunk destination index
interval = <integer> Input interval in seconds
run_only_one = <bool> set in defaults, must always be false to makes sure at Victoria stack input instance is running at each SHC host
start_by_shell = <bool> set in defaults, must always be false to make sure that modinput process is not wrapped into a shell. Wrapping into a shell on some OSs prevents input process form shutting down when it's disabled

[sqs_based_manager://<name>]
aws_sqs_url = <string> AWS SQS queue URL
aws_sqs_ignore_before  = <string> datetime in form of YYYY-MM-DD HH:MM marking max age of SQS messages to be processed
aws_sqs_visibility_timeout = <integer> AWS SQS queue visibility timeout in seconds
aws_collection = <string> Name of an FDR AWS collection defined in splunk_ta_crowdstrike_fdr_aws_collections.conf
cs_event_encoding = <string> Encoding of the events stored at CrowdStrike feed, in most cases it's utf-8
cs_ithr_type = <string> Defines which host resolution method to use if any. Values "inventory", "device_api" or no value are supported.
cs_event_filter_name = <string> Name of a CrowdStrike event filter defined in splunk_ta_crowdstrike_fdr_cs_event_filters.conf
cs_device_field_filter_name = <string> Name of a CrowdStrike device field event filter defined in splunk_ta_crowdstrike_fdr_cs_device_field_filter.conf
collect_external_events = <bool> 1 to collect external  security  events, otherwise 0
index_for_external_events = <string> optional separate index to store external  security  events
collect_ztha_events = <bool> 1 to collect zero trust host accessment  security  events, otherwise 0
index_for_ztha_events = <string> optional separate index to store zero trust host accessment  security  events
collect_inventory_aidmaster = <bool> 1 to collect aidmaster inventory events, otherwise 0
index_for_aidmaster_events = <string> optional separate index to store aidmaster inventory events
collect_inventory_managedassets = <bool> 1 to collect managedassets inventory events, otherwise 0
index_for_managedassets_events = <string> optional separate index to store managedassets inventory events
collect_inventory_notmanaged = <bool> 1 to collect notmanaged inventory events, otherwise 0
index_for_notmanaged_events = <string> optional separate index to store notmanaged inventory events
collect_inventory_appinfo = <bool> 1 to collect appinfo inventory events, otherwise 0
index_for_appinfo_events = <string> optional separate index to store appinfo inventory events
collect_inventory_userinfo = <bool> 1 to collect userinfo inventory events, otherwise 0
index_for_userinfo_events = <string> optional separate index to store userinfo inventory events
checkpoint_type = <string>  Type of checkpoint to use. Can take one of the two values: "sqs" or "internal"
index = <string>  Splunk destination index
interval = <integer> Input interval in seconds
run_only_one = <bool> set in defaults, must always be true to makes sure at Victoria stack that only one input instance is running at SHC
start_by_shell = <bool> set in defaults, must always be false to make sure that modinput process is not wrapped into a shell. Wrapping into a shell on some OSs prevents input process form shutting down when it's disabled

[managed_consumer_input://<name>]
manager = <string> name of manager input
per_file_exec = <bool> 1 to stop input after each ingested data file, otherwise 0
interval = <integer> Input interval in seconds
run_only_one = <bool> set in defaults, must always be false to makes sure at Victoria stack input instance is running at each SHC host
start_by_shell = <bool> set in defaults, must always be false to make sure that modinput process is not wrapped into a shell. Wrapping into a shell on some OSs prevents input process form shutting down when it's disabled
