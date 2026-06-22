# @placement search-head, indexer
#
# Lookup definitions for Whisper Security TA.
#
# Defines KV Store lookups for enrichment cache and threat intelligence,
# and CSV lookups for risk factors, ASN lists, and DNS provider lists.
#

# ─── KV Store Cache Lookups ──────────────────────────────────────────────

[whisper_enrichment_cache]
collection = <string> KV Store collection name.
external_type = <string> Lookup type (kvstore).
fields_list = <string> Comma-separated list of fields returned by this lookup.

[whisper_precomputed_enrichment]
collection = <string> KV Store collection name.
external_type = <string> Lookup type (kvstore).
fields_list = <string> Comma-separated list of fields returned by this lookup.

[whisper_watchlist]
collection = <string> KV Store collection name.
external_type = <string> Lookup type (kvstore).
fields_list = <string> Comma-separated list of fields returned by this lookup.

# ─── Automatic Lookup Definitions ────────────────────────────────────────

[whisper_domain_lookup]
collection = <string> KV Store collection name.
external_type = <string> Lookup type (kvstore).
fields_list = <string> Comma-separated list of fields returned by this lookup.
filter = <string> Filter expression to restrict results to domain indicators.

[whisper_ip_lookup]
collection = <string> KV Store collection name.
external_type = <string> Lookup type (kvstore).
fields_list = <string> Comma-separated list of fields returned by this lookup.
filter = <string> Filter expression to restrict results to IP indicators.

# ─── Correlation Search Lookups ─────────────────────────────────────

[whisper_high_risk_asns]
filename = <string> CSV filename for high-risk ASN list.
max_matches = <integer> Maximum number of lookup matches per input row.

[whisper_dns_providers]
filename = <string> CSV filename for DNS provider list.
match_type = <string> Match type for wildcard nameserver patterns.
max_matches = <integer> Maximum number of lookup matches per input row.

[whisper_cdn_asns]
filename = <string> CSV filename for CDN ASN list.
max_matches = <integer> Maximum number of lookup matches per input row.

[whisper_org_asns]
filename = <string> CSV filename for organization ASN list.

[whisper_risk_factors]
filename = <string> CSV filename for risk factor definitions.

[whisper_watchlist_csv]
filename = <string> CSV filename for the watchlist export.

# ─── Attack Surface Monitoring Lookups ──────────────────────────────────

[whisper_dns_baseline]
collection = <string> KV Store collection name.
external_type = <string> Lookup type (kvstore).
fields_list = <string> Comma-separated list of fields returned by this lookup.

# ─── ES Threat Intelligence Lookups ──────────────────────────────────────

[whisper_ip_intel]
collection = <string> KV Store collection name.
external_type = <string> Lookup type (kvstore).
fields_list = <string> Comma-separated list of fields returned by this lookup.

[whisper_domain_intel]
collection = <string> KV Store collection name.
external_type = <string> Lookup type (kvstore).
fields_list = <string> Comma-separated list of fields returned by this lookup.
