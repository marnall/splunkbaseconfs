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

# The add-on does not ship correlation-search threshold or risk-score
# macros.
