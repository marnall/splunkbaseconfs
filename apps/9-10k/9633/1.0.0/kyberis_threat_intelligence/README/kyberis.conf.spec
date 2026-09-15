[kyberis]
base_url = <string>
* Base URL of the Kyberis API. Defaults to https://api.kyberis.ai.
* Must use https:// — requests carry the API key and indicator values.
* http:// is accepted only for local development targets (localhost,
* 127.0.0.0/8, ::1, *.localhost, host.docker.internal).
* Cached enrichment results are scoped to this URL: entries fetched from a
* different base_url are ignored and refetched.

api_prefix = <string>
* API path prefix that endpoint routes are mounted under. Defaults to /v2.

timeout_seconds = <integer>
* Per-request timeout in seconds. Defaults to 20.

max_retries = <integer>
* Number of retries for transient (connection/5xx) failures. Defaults to 2.

cache_ttl_seconds = <integer>
* Time-to-live for cached enrichment results in the KV Store cache.
* Defaults to 86400 (24 hours). Set to 0 to disable caching.

cim_min_threat = <string>
* Lowest kyberis_threat level (low, medium, or high) that the | kyberis
* command maps to CIM Threat Intelligence (threat_*) fields. In ES semantics
* those fields mark a threat match, so benign verdicts should not carry them.
* Defaults to "medium". Set to "low" to map every successful verdict;
* per-search suppression via | kyberis cim=false.

log_level = <string>
* Logging verbosity for the app's search commands and alert action: DEBUG,
* INFO, WARNING, or ERROR. Defaults to INFO. Credential material is redacted
* from log output at every level. Search-command log formatting can
* additionally be customized via local/logging.conf.

default_profile = <string>
* Name of the credential profile to use when a search does not specify one.
* Defaults to "default".

[profile::<name>]
* A named credential profile, used for per-user/per-team usage attribution.
* The API key itself is stored in Splunk secure storage (storage/passwords)
* under realm "kyberis" and username "<name>" — never in this file.

description = <string>
* Optional human-readable description of who/what this profile is for.
