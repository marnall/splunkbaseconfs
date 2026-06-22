# @placement search-head
#
# Event type definitions for Whisper Security TA.
#
# Maps sourcetypes to event types for CIM data model compliance
# and tag-based categorization.
#

[whisper_enrichment]
search = <string> Search constraint for enrichment events. Matches sourcetype="whisper:enrichment".

[whisper_threat_intel]
search = <string> Search constraint for threat intelligence events. Matches sourcetype="whisper:threat_intel".

[whisper_watchlist]
search = <string> Search constraint for watchlist events. Matches sourcetype="whisper:watchlist".
