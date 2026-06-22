# @placement search-head
#
# Tag definitions for Whisper Security TA.
#
# Tags connect event types to CIM data models (Network Traffic,
# DNS, Threat Intelligence).
#

[eventtype=whisper_enrichment]
network = <string> Tag for CIM Network Traffic data model. Set to "enabled".
resolution = <string> Tag for CIM DNS resolution data model. Set to "enabled".
dns = <string> Tag for CIM DNS data model. Set to "enabled".

[eventtype=whisper_threat_intel]
threat = <string> Tag for CIM Threat Intelligence data model. Set to "enabled".
report = <string> Tag for CIM report category. Set to "enabled".

[eventtype=whisper_watchlist]
threat = <string> Tag for CIM Threat Intelligence data model. Set to "enabled".
report = <string> Tag for CIM report category. Set to "enabled".

[eventtype=whisper_attack_surface]
network = <string> Tag for CIM Network Traffic data model. Set to "enabled".
communicate = <string> Tag for CIM network communication category. Set to "enabled".

[eventtype=whisper_attack_surface_change]
change = <string> Tag for CIM Change Analysis data model. Set to "enabled".
