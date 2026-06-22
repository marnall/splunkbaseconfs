# @placement search-head, indexer
#
# Field alias and extraction definitions for Whisper Security TA.
#
# CIM-compliant field mapping for enriched events. Whisper enrichment
# fields use the whisper_ prefix and are aliased to CIM equivalents.
#

# ─── JSON Field Extraction ────────────────────────────────────────────

[whisper:health]
KV_MODE = <string> Field extraction mode. Set to json for automatic JSON parsing.

[whisper:attack_surface]
KV_MODE = <string> Field extraction mode. Set to json for automatic JSON parsing.

[whisper:threat_intel]
KV_MODE = <string> Field extraction mode. Set to json for automatic JSON parsing.

[whisper:watchlist]
KV_MODE = <string> Field extraction mode. Set to json for automatic JSON parsing.

[whisper:change]
KV_MODE = <string> Field extraction mode. Set to json for automatic JSON parsing.

# ─── CIM Field Aliases ───────────────────────────────────────────────

[whisper:enrichment]
FIELDALIAS-whisper_dest_ip = <string> Alias whisper_ip to CIM dest_ip.
FIELDALIAS-whisper_dest_country = <string> Alias whisper_country to CIM dest_country.
FIELDALIAS-whisper_dest_asn = <string> Alias whisper_asn to CIM dest_asn.
FIELDALIAS-whisper_threat_score = <string> Alias whisper_threat_score to CIM threat_score.
FIELDALIAS-whisper_threat_level = <string> Alias whisper_threat_level to CIM threat_level.
FIELDALIAS-whisper_is_threat = <string> Alias whisper_is_threat to CIM is_threat.
FIELDALIAS-whisper_is_c2 = <string> Alias whisper_is_c2 to CIM is_c2.
FIELDALIAS-whisper_is_tor = <string> Alias whisper_is_tor to CIM is_tor.
FIELDALIAS-whisper_is_malware = <string> Alias whisper_is_malware to CIM is_malware.
FIELDALIAS-whisper_is_phishing = <string> Alias whisper_is_phishing to CIM is_phishing.
FIELDALIAS-whisper_is_anonymizer = <string> Alias whisper_is_anonymizer to CIM is_anonymizer.
FIELDALIAS-whisper_is_spam = <string> Alias whisper_is_spam to CIM is_spam.
FIELDALIAS-whisper_is_bruteforce = <string> Alias whisper_is_bruteforce to CIM is_bruteforce.
FIELDALIAS-whisper_is_scanner = <string> Alias whisper_is_scanner to CIM is_scanner.
FIELDALIAS-whisper_is_blacklist = <string> Alias whisper_is_blacklist to CIM is_blacklist.
FIELDALIAS-whisper_is_proxy = <string> Alias whisper_is_proxy to CIM is_proxy.
FIELDALIAS-whisper_is_vpn = <string> Alias whisper_is_vpn to CIM is_vpn.
FIELDALIAS-whisper_is_whitelist = <string> Alias whisper_is_whitelist to CIM is_whitelist.
FIELDALIAS-whisper_risk_score = <string> Alias whisper_risk_score to CIM risk_score.
FIELDALIAS-whisper_risk_level = <string> Alias whisper_risk_level to CIM risk_level.
EVAL-vendor = <string> Static vendor field set to "Whisper Security".
EVAL-vendor_product = <string> Static vendor product field set to "Whisper Knowledge Graph".

[whisper:spf_compliance]
KV_MODE = <string> Field extraction mode. Set to json for automatic JSON parsing.
FIELDALIAS-last_checked = <string> Alias collected_at to last_checked.

[whisper:dnssec_compliance]
KV_MODE = <string> Field extraction mode. Set to json for automatic JSON parsing.
FIELDALIAS-last_checked = <string> Alias collected_at to last_checked.
