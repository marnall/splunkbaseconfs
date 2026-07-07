[rfes_ar_enrichment]
param.category = <string>
    * Specify what type of entity is being enriched.
    * Allowed values are ip, domain, hash, vulnerability, url or auto.
    * Required.
    * Defaults to auto.
param.field = <string>
    * The field name containing the value to be used.
    * Required parameter
param.prefix = <string>
    * The prefix contains Finding (Notable Event) title prefix.
    * Default: Threat Activity Enriched.
    * Required parameter

[rfes_ar_links]
param.category = <string>
    * Specify what type of entity is being enriched.
    * Allowed values are ip, domain, hash, vulnerability, url or auto.
    * Required.
    * Defaults to auto.
param.field = <string>
    * The field name containing the value to be used.
    * Required parameter
param.index = <string>
    * Where to perform the threat hunt
    * Required parameter
param.earliest = <string>
    * How far back in time do we want to search
    * Default: -4w
    * Required parameter
param.notable = <bool>
    * Store results in notable index y/n
    * Default: 1
    * Required parameter
param.risk = <bool>
    * Store results in risk index y/n
    * Default: 0
    * Required parameter


[rfes_ar_collective_insights]
param.detection_action = <string>
    * What field from the notable should be mapped to 'action'.
    * Type: String
    * Defaults to 'action'
param.ioc_value = <string>
    * What field from the notable contain the indicator.
    * Type: String
    * Required parameter
param.use_case_name = <string>
    * What value from the notable should map to "descritption".
    * Type: String
    * Required parameter
param.source_type = <string>
    * What value from the notable should map to "Event Source".
    * Type: String
param.timestamp = <string>
    * What value from the notable should map to "Event time".
    * Type: String
    * Defaults to _time
param.ioc_type = auto
    * Specify what type of entity is being enriched.
    * Allowed values are ip, domain, hash, vulnerability, url or auto.
    * Required parameter
    * Defaults to auto.