[fortindr_cloud_entities://<name>]
entities = Enter one or more entities (IP address or domain) separated by commas to search for entity enrichment information from FortiNDR Cloud.
fetch_pdns = Include Passive DNS enrichment data in the response (unchecked by default).
fetch_dhcp = Include DHCP enrichment data in the response (unchecked by default).
fetch_vt = Include Virus Total enrichment data in the response (unchecked by default).

[fortindr_cloud_events://<name>]
aws_access_key = The AWS Access Key to connect to the S3 buckets.
aws_secret_key = The AWS Secret Key to connect to the S3 Buckets.
aws_bucket_name = The AWS Bucket Name to connect to the S3 Bucket.
account_code = Account code of the account we want to query.
event_types = List of Event Types to be retrieved.
days_to_collect = The amount of days of historical data that need to be retrieved. The allowed values are integer from 0 to 7. By default, no historical data is retrieved.

[fortindr_cloud_detections://<name>]
start_date = Define if historical data is required (i.e. '2025-12-01T00:00:00.000Z'). By default, no historical data is retrieved.
polling_delay = Polling delay in minute. This is required to allow time for the detections to be processed before polling them.
account_uuid = Filter results to show only detections for the specified account UUID. If none is entered, detections will be pulled for all accounts you have access to.
status = Choose to pull detections that are active, resolved, or both.
severity_levels = Choose to pull detections for rules of a particular severity level. Default is to pull detections for all severities (high, moderate, and low).
confidence_levels = Choose to pull detections for rules of a particular confidence level. Default is to pull detections for all confidences (high, moderate, and low).
pull_muted_rules = Choose to pull detections for rules that are muted, unmuted, or both. Unmuted by default.
pull_muted_devices = Choose to pull detections for devices that are muted, unmuted, or both. Unmuted by default.
pull_muted_detections = Choose to pull detections that are muted, unmuted, or both. Unmuted by default.
include_description = Enable this option if you want to include the rule's description with the results. Checked by default.
include_signature = Enable this option if you want to include the rule IQL signature with the results. Checked by default.
include_pdns = Enable this option if you want to include passive DNS information for the impacted asset for each detection.
include_annotations = Enable this option if you want to include annotations information for the impacted asset for each detection.
include_events = Enable this option if you want to import the events associated with each detection. NOTE: This may pull a large amount of events into Splunk (up to 1000). Unchecked by default.