[insight_detections://<name>]
start_date = The first date to pull Insight detections from. If no date is entered, a default value of "2021-11-01T00:00:00.000Z" will be used.
account_uuid = Filter results to show only detections for the specified account UUID. If none is entered, detections will be pulled for all accounts you have access to.
status = Choose to pull detections that are active, resolved, or all (detections of any status).
severity_levels = Choose to pull detections for rules of a particular severity level. Default is to pull detections for all severities (high, moderate, and low).
confidence_levels = Choose to pull detections for rules of a particular confidence level. Default is to pull detections for all confidences (high, moderate, and low).
pull_muted_rules = Choose to pull detections for rules that are muted, unmuted, or all (both muted and unmuted rules). Default is to pull only detections for unmuted rules.
pull_muted_devices = Choose to pull detections for devices that are muted for the account, unmuted devices, or all (both muted and unmuted devices for the account). Default is to pull only detections for unmuted devices.
pull_muted_detections = Choose to pull detections that are muted, unmuted, or all (both muted and unmuted detections). Default is to pull only unmuted detections.
include_description = Enable this option if you want to include the detection description with the results. Default is to include the description when pulling detections.
include_signature = Enable this option if you want to include the detection IQL signature with the results. Default is to include the signature when pulling detections.
include_pdns = Enable this option if you want to include passive DNS information for the impacted asset for each detection.
include_dhcp = Enable this option if you want to include DHCP information for the impacted asset for each detection.
include_events = Enable this option if you want to import the events associated with each detection. NOTE: This may pull a large amount of events into Splunk (up to 1000).
filter_training_detections = Filter out detections from the training environment. This is checked off by default and recommended.

[insight_entity://<name>]
entities = Enter one or more entities (IP address or domain) separated by commas to search for entity enrichment information from Insight.
fetch_pdns = Include Passive DNS enrichment data in the response (default is checked).
fetch_dhcp = Include DHCP enrichment data in the response (default is checked).
filter_training_data = Filter pdns and dhcp data from the training environment. This is checked by default and recommended.

[insight_query://<name>]
aws_access_key = The AWS Access Key to connect to the S3 buckets
aws_secret_key = The AWS Secret Key to connect to the S3 Buckets
account_code = Account code of the account we want to query.
event_types = List of Event Types to be retrieved.
days_to_collect = The amount of days we must go back to retrieve the events (maximum 7 days). If no value is entered, or if the entered value is greater than 7, only events from the last 7 days will be retrieved.
fetch_pdns = Enable this to fetch passive DNS entity enrichment information for IPs in the query results. Will fetch this information for both internal and external IPs.
fetch_dhcp = Enable this to fetch DHCP lease entity enrichment information for IPs in the query results. Will only fetch this information for internal IPs.