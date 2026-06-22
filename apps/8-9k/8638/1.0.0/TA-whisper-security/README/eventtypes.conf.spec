# @placement search-head
#
# Event type definitions for Whisper Security TA.
#
# Maps sourcetypes to event types for CIM data model compliance
# and tag-based categorization.
#

[whisper_enrichment]
search = <string> Search constraint for enrichment events. Matches sourcetype="whisper:enrichment".

[whisper_health]
search = <string> Search constraint for health check events. Matches sourcetype="whisper:health".

[whisper_threat_intel]
search = <string> Search constraint for threat intelligence events. Matches sourcetype="whisper:threat_intel".

[whisper_attack_surface]
search = <string> Search constraint for attack surface events. Matches sourcetype="whisper:attack_surface".

[whisper_watchlist]
search = <string> Search constraint for watchlist events. Matches sourcetype="whisper:watchlist".

[whisper_attack_surface_change]
search = <string> Search constraint for attack surface change events. Matches sourcetype="whisper:attack_surface_change".
