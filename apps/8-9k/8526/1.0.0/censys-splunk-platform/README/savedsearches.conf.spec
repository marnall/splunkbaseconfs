# This file contains the specification for savedsearches.conf
# It documents the configuration options available for saved searches in the Censys app

# Common settings for all saved searches
# These are standard Splunk settings
disabled = [0|1]
enableSched = [0|1]
description = <string>
dispatch.earliest_time = <string>
dispatch.latest_time = <string>
cron_schedule = <string>
search = <string>

# Censys notable index enrichment saved searches
# These searches automatically enrich notable events with Censys data

[censys_notable_index_host_enrichment]
* Periodically enriches hosts from notables with Censys API
* Extracts IP addresses from notables and enriches them
* Uses the censys_reactive_alert_enrichment_triage_es alert action

[censys_notable_index_web_property_enrichment]
* Periodically enriches web properties from notables with Censys API
* Extracts domain:port combinations from notables and enriches them
* Uses the censys_reactive_alert_enrichment_triage_es alert action

[censys_notable_index_certificate_enrichment]
* Periodically enriches certificates from notables with Censys API
* Extracts SHA256 hashes from notables and enriches them
* Uses the censys_reactive_alert_enrichment_triage_es alert action

# Censys lookup maintenance saved searches
# These searches perform periodic cleanup of lookup data

[censys_purge_host_enrichment_lookup]
* Periodically removes entries older than 30 days from censys_host_enrichment_lookup

[censys_purge_web_property_enrichment_lookup]
* Periodically removes entries older than 30 days from censys_web_property_enrichment_lookup

[censys_purge_certificate_enrichment_lookup]
* Periodically removes entries older than 30 days from censys_certificate_enrichment_lookup

[censys_purge_host_event_history_lookup]
* Periodically removes entries older than 30 days from censys_host_event_history_lookup

# Parameters for the alert actions
param.global_account = <string>
* The Censys account name to use for enrichment

param.indicator_type = <string>
* The type of indicator to enrich
* Valid values: host, web_property, certificate

param.field_name = <string>
* The field containing the value to enrich

param.scan_type = <string>
* The type of scan to perform