# @placement search-head
#
# Saved search definitions for Whisper Security TA.
#
# This file defines internal utility searches and disabled example
# enrichment pipeline templates. The add-on does not ship prebuilt
# correlation searches.
#
# All stanzas ship with disabled = 1.
#

[Whisper - Evict Expired Cache Entries]
description = <string> Description of the saved search.
disabled = <bool> Whether the search is disabled. Default: 1.
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search string.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.

[Whisper - Populate IP Threat Intel KV Store]
description = <string> Description of the saved search. Populates the whisper_ip_intel collection from the Whisper Graph for ES Threat Intelligence framework integration.
disabled = <bool> Whether the search is disabled. Default: 1.
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search string that queries the Whisper Graph and writes results to the whisper_ip_intel KV Store collection.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.

[Whisper - Populate Domain Threat Intel KV Store]
description = <string> Description of the saved search. Populates the whisper_domain_intel collection from the Whisper Graph for ES Threat Intelligence framework integration.
disabled = <bool> Whether the search is disabled. Default: 1.
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search string that queries the Whisper Graph and writes results to the whisper_domain_intel KV Store collection.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.

[Whisper - Populate Precomputed Enrichment KV Store]
description = <string> Description of the saved search. Pre-warms the whisper_precomputed_enrichment KV Store collection with enrichment data for frequently used indicators.
disabled = <bool> Whether the search is disabled. Default: 1.
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search string that runs whisperlookup across a set of indicators and writes the enriched rows to the whisper_precomputed_enrichment collection.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.

[Example - Whisper - Enrich DNS Domains]
description = <string> Description of the saved search. Example enrichment pipeline template that enriches DNS query domains with Whisper Graph context.
disabled = <bool> Whether the search is disabled. Default: 1.
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search string. Clone the stanza and edit source_index, indicator field, and destination_index before enabling.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.

[Example - Whisper - Enrich Destination IPs]
description = <string> Description of the saved search. Example enrichment pipeline template that enriches destination IP addresses from network traffic with Whisper Graph context.
disabled = <bool> Whether the search is disabled. Default: 1.
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search string. Clone the stanza and edit source_index, indicator field, and destination_index before enabling.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.

[Example - Whisper - Enrich Proxy Hostnames]
description = <string> Description of the saved search. Example enrichment pipeline template that enriches proxy/web hostnames with Whisper Graph context.
disabled = <bool> Whether the search is disabled. Default: 1.
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search string. Clone the stanza and edit source_index, indicator field, and destination_index before enabling.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.

[Example - Whisper - Custom Graph Query Enrichment]
description = <string> Description of the saved search. Example template that runs a custom Cypher query against the Whisper Graph. The indicator token is validated against a strict character allowlist before being interpolated into the Cypher query to prevent injection.
disabled = <bool> Whether the search is disabled. Default: 1.
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search string. Edit the Cypher query, indicator parameter, and destination_index before enabling.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
