# @placement search-head
#
# KV Store collection definitions for Whisper Security TA.
#
# Collections store enrichment cache data, threat intelligence,
# and attack surface monitoring baselines.
#

[whisper_enrichment_cache]
enforceTypes = <bool> Whether to enforce field type validation.
field.indicator = <string> Indicator value (domain, IP, etc.)
field.indicator_type = <string> Type of indicator (domain, ip)
field.enrichment_data = <string> JSON-encoded enrichment results
field.cached_at = <number> Epoch timestamp when cached
field.ttl_seconds = <number> Cache time-to-live in seconds
accelerated_fields.indicator_idx = <json> Index on indicator and indicator_type for fast lookups.

[whisper_precomputed_enrichment]
enforceTypes = <bool> Whether to enforce field type validation.
field.indicator = <string> Indicator value
field.indicator_type = <string> Type of indicator
field.enrichment_data = <string> JSON-encoded enrichment results
field.enriched_at = <number> Epoch timestamp when enriched
accelerated_fields.indicator_idx = <json> Index on indicator and indicator_type for fast lookups.

[whisper_ip_intel]
enforceTypes = <bool> Whether to enforce field type validation.
field.ip = <string> IP address indicator
field.threat_collection_name = <string> ES threat collection name
field.threat_collection_key = <string> ES threat collection key
field.description = <string> Threat description
field.threat_key = <string> Threat key identifier
field.threat_group = <string> Threat group attribution
field.weight = <number> Threat weight/severity
field.whisper_asn = <string> Autonomous System Number
field.whisper_asn_name = <string> ASN organization name
field.whisper_country = <string> Country code
field.whisper_prefix = <string> BGP prefix
field.whisper_risk_score = <number> Whisper composite risk score (0-100)
field.whisper_risk_level = <string> Risk level (low, medium, high, critical)
field.whisper_threat_score = <number> Threat intelligence score (0-100)
field.whisper_threat_level = <string> Threat level (low, medium, high, critical)
accelerated_fields.ip_idx = <json> Index on ip for fast lookups.

[whisper_domain_intel]
enforceTypes = <bool> Whether to enforce field type validation.
field.domain = <string> Domain indicator
field.threat_collection_name = <string> ES threat collection name
field.threat_collection_key = <string> ES threat collection key
field.description = <string> Threat description
field.threat_key = <string> Threat key identifier
field.threat_group = <string> Threat group attribution
field.weight = <number> Threat weight/severity
field.whisper_asn_name = <string> ASN organization name
field.whisper_country = <string> Country code
field.whisper_risk_score = <number> Whisper composite risk score (0-100)
field.whisper_risk_level = <string> Risk level (low, medium, high, critical)
field.whisper_threat_score = <number> Threat intelligence score (0-100)
field.whisper_threat_level = <string> Threat level (low, medium, high, critical)
accelerated_fields.domain_idx = <json> Index on domain for fast lookups.

[whisper_watchlist]
enforceTypes = <bool> Whether to enforce field type validation.
field.indicator = <string> Indicator value (domain, IP, etc.)
field.indicator_type = <string> Type of indicator (domain, ip)
field.description = <string> Description of why this indicator is watched
accelerated_fields.indicator_idx = <json> Index on indicator and indicator_type for fast lookups.

[whisper_dns_baseline]
enforceTypes = <bool> Whether to enforce field type validation.
field.domain = <string> Domain being monitored
field.record_type = <string> DNS record type (A, AAAA, CNAME, NS, MX)
field.record_value = <string> DNS record value
field.collected_at = <string> ISO timestamp of collection
field.collection_id = <string> Collection batch identifier
field.client_id = <string> Multi-tenant client identifier
accelerated_fields.domain_idx = <json> Index on domain and record_type for fast lookups.
