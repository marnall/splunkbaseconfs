# @placement search-head
#
# Search macro definitions for Whisper Security TA.
#
# Macros provide reusable graph query patterns for common
# infrastructure investigations and configurable thresholds
# for correlation search sensitivity.
#

# ─── Index Macro ──────────────────────────────────────────────────────

[whisper_index]
description = <string> Human-readable description of this macro.
definition = <string> Default index for Whisper Security events. Override to use a custom index name.
iseval = <bool> Whether the definition is an eval expression.

# ─── Graph Query Macros ──────────────────────────────────────────────

[whisper_shared_nameservers(1)]
description = <string> Human-readable description of this macro.
args = <string> Macro argument name (domain).
definition = <string> Whisperquery command to find domains sharing nameservers with the given domain.

[whisper_asn_infrastructure(1)]
description = <string> Human-readable description of this macro.
args = <string> Macro argument name (asn).
definition = <string> Whisperquery command to enumerate all prefixes routed by an ASN.

[whisper_cname_chain(1)]
description = <string> Human-readable description of this macro.
args = <string> Macro argument name (domain).
definition = <string> Whisperquery command to resolve the CNAME chain for a domain.

[whisper_spf_chain(1)]
description = <string> Human-readable description of this macro.
args = <string> Macro argument name (domain).
definition = <string> Whisperquery command to trace the SPF include chain for a domain.

[whisper_bgp_peers(1)]
description = <string> Human-readable description of this macro.
args = <string> Macro argument name (asn).
definition = <string> Whisperquery command to list BGP peers of an ASN.

[whisper_cohosted_domains(1)]
description = <string> Human-readable description of this macro.
args = <string> Macro argument name (domain).
definition = <string> Whisperquery command to find domains co-hosted on the same IP.

[whisper_full_investigation(1)]
description = <string> Human-readable description of this macro.
args = <string> Macro argument name (indicator).
definition = <string> Whisperquery command for full infrastructure investigation: hostname to IP to ASN with geo.

[whisper_explain(1)]
description = <string> Human-readable description of this macro.
args = <string> Macro argument name (indicator).
definition = <string> Whisperquery command to get threat assessment via the Whisper explain API.

# ─── Correlation Search Threshold Macros ─────────────────────────────────

[whisper_cname_depth_threshold]
description = <string> Human-readable description of this macro.
definition = <integer> Maximum CNAME chain depth before alerting.
iseval = <bool> Whether the definition is an eval expression.

[whisper_newly_observed_domain_age_hours]
description = <string> Human-readable description of this macro.
definition = <integer> Time window (hours) for considering a domain newly observed.
iseval = <bool> Whether the definition is an eval expression.

[whisper_fast_flux_ip_threshold]
description = <string> Human-readable description of this macro.
definition = <integer> Minimum distinct IPs for fast-flux flagging.
iseval = <bool> Whether the definition is an eval expression.

[whisper_low_cohosting_max]
description = <string> Human-readable description of this macro.
definition = <integer> Maximum co-hosting count for low-density anomaly detection.
iseval = <bool> Whether the definition is an eval expression.

[whisper_multi_feed_threshold]
description = <string> Human-readable description of this macro.
definition = <integer> Minimum distinct threat feeds for multi-feed correlation.
iseval = <bool> Whether the definition is an eval expression.

[whisper_newly_registered_domain_days]
description = <string> Human-readable description of this macro.
definition = <integer> Maximum domain age in days for newly-registered detection.
iseval = <bool> Whether the definition is an eval expression.

[whisper_tor_risk_score]
description = <string> Human-readable description of this macro.
definition = <integer> Risk score assigned to TOR exit node communication events.
iseval = <bool> Whether the definition is an eval expression.

[whisper_bulletproof_risk_score]
description = <string> Human-readable description of this macro.
definition = <integer> Risk score assigned to bulletproof ASN communication events.
iseval = <bool> Whether the definition is an eval expression.

[whisper_bgp_conflict_risk_score]
description = <string> Human-readable description of this macro.
definition = <integer> Risk score assigned to BGP prefix conflict events.
iseval = <bool> Whether the definition is an eval expression.
