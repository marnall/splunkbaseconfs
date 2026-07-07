[trustar_splunk_es_ingest_iocs://<name>]
global_account = The set of API credentials for a TruSTAR user account. This setting is REQUIRED.
enclave_ids = A comma separated list of IDs of enclaves to pull from. This setting is REQUIRED.
ioc_types = The list of IOC types to pull. This setting is REQUIRED.
tags = A comma-separated list of tag names. Splunk will only add indicators that have ALL of these tags. If empty, no tags will be required.
expiration_days = IOCs older than this time will be expired from Splunk.  This setting is REQUIRED.