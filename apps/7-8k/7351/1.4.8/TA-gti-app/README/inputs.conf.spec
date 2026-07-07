[threat_lists://<name>]
index = (Default: default)
interval = Time interval of input in seconds. (Default: 3600)
sync_es_threat_intelligence = 
threat_lists_category = 
threat_lists_filter = Leave blank to query all threat lists, or enter a custom filter.

[ioc_stream://<name>]
index = (Default: default)
interval = Time interval of input in seconds. (Default: 3600)
ioc_stream_filter = Leave blank to query all IoC stream notifications, or enter a custom filter.
sync_es_threat_intelligence = 

[cve://<name>]
exploitation_state = 
index = (Default: gti_cve_internal)
interval = Time interval of input in seconds.
risk_rating = 
