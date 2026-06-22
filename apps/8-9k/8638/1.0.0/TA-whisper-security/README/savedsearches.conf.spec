# @placement search-head
#
# Saved search and correlation search definitions for Whisper Security TA.
#
# All correlation searches are disabled by default. Administrators
# enable them per their environment requirements.
#

# ─── Cache Maintenance ────────────────────────────────────────────────

[Whisper - Evict Expired Cache Entries]
description = <string> Description of the saved search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search string.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.

# ─── Correlation Searches: DNS/Infrastructure Intelligence ────────────

[Whisper - Bulletproof ASN Communication Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search string using Network_Traffic data model and whisper_high_risk_asns lookup.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object (system, user, etc.).
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Shared Nameserver with Threat Infrastructure]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search string using Network_Resolution data model and whisper_dns_providers lookup.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - DNS Infrastructure Change Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search comparing whisper_dns_baseline against current enrichment data.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Newly Observed Domain Communication]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting communication with newly observed domains.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Suspicious CNAME Chain Depth]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting suspiciously deep CNAME chains.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Fast Flux Domain Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting domains with rapid IP rotation (fast-flux).
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Domain Typosquatting Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting typosquatting domain communication.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

# ─── Correlation Searches: Infrastructure Pivot Detection ─────────────

[Whisper - Low Co-Hosting Density Anomaly]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting IPs with low co-hosting density on non-CDN ASNs.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Infrastructure Pivot Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting infrastructure pivots between threat and legitimate domains.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Shared Hosting with Known Threat Infrastructure]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting domains sharing hosting with known threats.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Domain Parking and Sinkhole Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting parked or sinkholed domains.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Mail Server Infrastructure Change]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting MX record infrastructure changes.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

# ─── Correlation Searches: Network/BGP Intelligence ───────────────────

[Whisper - BGP Prefix Conflict Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting BGP prefix conflicts via Whisper graph data.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Shadow IT DNS Provider Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting unauthorized DNS providers for organizational domains.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Unauthorized Subdomain Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting unauthorized subdomains via DNS baseline comparison.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - ASN Migration Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting ASN migration for monitored domains.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Nameserver Delegation Change]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting nameserver delegation changes for monitored domains.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

# ─── Correlation Searches: Threat Intel Correlation ───────────────────

[Whisper - Multi-Feed Threat IP Communication]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting communication with IPs on multiple threat feeds.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Newly Registered Domain Resolution]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting DNS resolution to newly registered domains.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - TOR Exit Node Communication]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting communication with TOR exit nodes.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

# ─── Correlation Searches: Graph Utilization ──────────────────────────

[Whisper - Impossible Travel Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting impossible travel patterns via GeoIP correlation.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - WHOIS Contact Correlation]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting shared WHOIS contact information with threat infrastructure.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - BGP Hijack Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting potential BGP hijack events.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Registrar Change Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting domain registrar changes.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Newly Registered Domain Risk]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting communication with newly registered domains.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Privacy-Proxied WHOIS Alert]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting communication with privacy-proxied WHOIS domains.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Prefix-Level Threat Detection]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting communication with IPs on threat-flagged BGP prefixes.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - HOSTNAME Direct Threat Properties]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting communication with hostnames having direct threat properties.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

[Whisper - Suspicious Web Link Profile]
description = <string> Description of the correlation search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search detecting domains with suspicious inbound/outbound web link profiles.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
action.risk = <bool> Whether risk action is enabled.
action.risk.param._risk_object = <string> Field containing the risk object.
action.risk.param._risk_object_type = <string> Type of risk object.
action.risk.param._risk_score = <integer> Base risk score for this detection.

# ─── KV Store Population Searches ─────────────────────────────────────

[Whisper - Populate IP Threat Intel KV Store]
description = <string> Description of the saved search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search to populate IP threat intel KV Store from enrichment data.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.

[Whisper - Populate Domain Threat Intel KV Store]
description = <string> Description of the saved search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search to populate domain threat intel KV Store from enrichment data.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.

[Whisper - Populate Precomputed Enrichment KV Store]
description = <string> Description of the saved search.
disabled = <bool> Whether the search is disabled. Default: 1 (disabled).
cron_schedule = <string> Cron schedule expression.
search = <string> SPL search to populate precomputed enrichment KV Store for watchlist domains.
dispatch.earliest_time = <string> Earliest time for the search window.
dispatch.latest_time = <string> Latest time for the search window.
enableSched = <bool> Whether scheduling is enabled. Default: 0.
is_visible = <bool> Whether the search is visible in the UI.
