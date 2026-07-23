# k8s_search.conf.spec — schema for the app-wide runtime settings.
#
# Lives at $SPLUNK_HOME/etc/apps/os_k8s_search/{default,local}/k8s_search.conf.
# default/ is shipped by the app; operators should edit only local/.
# AppInspect validates any local/ file shipped or installed by an
# operator against this spec.

[splunk]
* Interactions with the local splunkd REST API.

request_timeout = <duration>
* Timeout for a single REST call to the local splunkd — used at search
* time to read the stored cluster credentials. Any other splunkd REST
* call the app makes uses the same value.
* Go duration string (e.g. "30s", "1m"). Default: 30s.
* Raise only when splunkd is genuinely slow (a large or geographically
* distributed search head cluster); over ~5s for a localhost call means
* splunkd itself is struggling.

tls_ca_file = <path>
* PEM CA bundle used to verify splunkd's certificate. Env vars in the
* path ($SPLUNK_HOME etc.) are expanded.
* Default: $SPLUNK_HOME/etc/auth/cacert.pem (the CA Splunk Enterprise
* generates on first start).
* If the file is missing or unreadable, the app skips verification for
* that read (logging a warning) instead of failing outright — this covers
* non-standard installs where the CA lives elsewhere.

tls_cert_file = <path>
* splunkd's own certificate. When tls_server_name_from_cert is true and
* the splunkd URL is loopback (127.0.0.0/8, ::1, localhost), the app
* verifies splunkd by pinning to this exact certificate file rather than
* checking a hostname.
* Default: $SPLUNK_HOME/etc/auth/server.pem. The file may hold both the
* certificate and its private key; only the certificate is used.

tls_server_name = <hostname>
* Hostname the splunkd certificate must match. When set, it takes
* precedence over tls_server_name_from_cert and the app verifies splunkd
* by the standard check (certificate chain + hostname match).
* Use this only if you have replaced splunkd's certificate with one that
* carries a proper DNS SAN. Splunk's default self-signed certificate does
* not, so on a stock install leave this empty and keep
* tls_server_name_from_cert = true instead.
* Default: empty.

tls_server_name_from_cert = <boolean>
* When true (default) and the splunkd URL is loopback, the app verifies
* splunkd by pinning to the exact certificate file at tls_cert_file
* instead of matching a hostname. This is the right choice for a stock
* Splunk install, whose default certificate has no hostname to match.
*
* Pinning is restricted to loopback URLs: it is safe precisely because
* the certificate on disk is the one local splunkd will present. For a
* non-loopback splunkd URL this setting is ignored and the standard
* hostname check against the URL host applies.
* Default: true.

tls_insecure = <boolean>
* When true, skip certificate verification entirely for credential reads
* against splunkd. Use only when verification is genuinely impossible (a
* replaced certificate whose CA the app cannot reach, or an unusual
* install layout). Requests are still authenticated by the Splunk session
* key; only the certificate check is dropped.
* Default: false.

[kubernetes]
* Interactions with the cluster's API server: per-request timeouts,
* multi-cluster parallelism, and the container-log line-size cap.

api_request_timeout = <duration>
* Caps non-streaming Kubernetes API requests (Discover, List, Get)
* issued by the `| k8s` search command. The K8s API server already
* enforces its own timeoutSeconds; this is a wall-clock bound from
* the search side so a hung TCP connection doesn't leave a stuck
* search around.
* Go duration string. Default: 30s.

logs_api_request_timeout = <duration>
* Caps requests issued by `| k8slogs`. Default 30s. A non-positive
* value (including 0) is treated as "use the default" — 0 does NOT
* mean "unbounded". `| k8slogs` returns a bounded log snapshot (there
* is no live follow mode), so 30s suits the common case; set a larger
* explicit value only if a big `tail=` / `since=` read needs longer.
* Go duration string. Default: 30s.

fan_out_concurrency = <integer>
* Caps how many clusters are queried in parallel during a
* multi-cluster fan-out (`context=*`). Also caps how many container
* log streams `| k8slogs` opens in parallel per cluster, so a
* `pods=*` search in a large namespace paces its `/log` requests
* instead of opening one per matching container at once.
* Operators running unusually wide fan-outs (50+ clusters) may want a
* higher value; very small search heads may want a lower one to keep
* CPU off the search-head box. The SPL `concurrency=N` per-search
* override wins (cluster fan-out only), capped at 128.
* Default: 8.

max_log_line_bytes = <integer>
* Maximum size of a single container log line. Runtimes usually split
* very long lines, but init-container bootstraps and JVM stack traces can
* emit single lines over 100 KB. Raise this if you see a "token too long"
* error in the search log.
* Default: 1048576 (1 MiB).

[logging]
* Search-command log output. This is the master source for log
* destination + verbosity; the keys below are the package defaults
* every `| k8s` and `| k8slogs` search uses. The binary also
* accepts --log-file / --log-level on the command line for ad-hoc
* troubleshooting; the conf-file values supersede the flags.

level = <trace|debug|info|warn|error|fatal>
* Master log level applied to every component without an explicit
* override in [logging] levels.* keys. Default: info.

file = <path>
* Log output file path. Relative paths resolve to the per-search
* dispatch directory (splunkd auto-cleans these); absolute paths
* go where you point them — operator-managed rotation required.
* Env vars in the path ($SPLUNK_HOME etc.) are expanded.
* Default: k8s_search.log (relative, lands in the dispatch dir).
*
* Example — write to a persistent location splunkd indexes into
* index=_internal (operator owns rotation):
*   file = $SPLUNK_HOME/var/log/k8s_search.log

levels.<component> = <trace|debug|info|warn|error|fatal>
* Per-component log-level overrides. <component> is one of the component
* names listed below; the longest matching prefix wins, so a key like
* "levels.k8s_search/internal" sets the level for every component under
* that path at once.
*
* Available components in this binary:
*
*   k8s_search/internal/conn               connection resolution + secrets
*   k8s_search/internal/get                `| k8s` command lifecycle
*   k8s_search/internal/logs               `| k8slogs` command lifecycle
*   core/kubernetes/api                   Kubernetes API HTTP calls
*   core/httpx                            HTTP transport / TLS / retry
*   core/splunk/chunked_custom_search     Splunk chunked search protocol
*
* Examples:
*   levels.k8s_search/internal/conn = debug
*   levels.core/kubernetes/api = trace

[cache]
* Disk-backed cache for Kubernetes API responses. Three layers:
* discovery (10-min TTL), LIST results (30s default), and GET
* single-object reads (10s default). The directory is swept
* every 5 minutes by the scripted-input
* `[script://./bin/cache_sweep.py]` in inputs.conf.

enabled = <boolean>
* Master on/off switch for the disk cache. When false, every search runs
* uncached (both the discovery and response layers are off). If the cache
* directory becomes unwritable the app turns the disk cache off
* automatically for that search; setting this to false makes that choice
* permanent and visible in your conf file.
* Scope: this controls the disk cache only. It does not change the app's
* retry/backoff behavior, nor a short-lived in-memory discovery cache the
* app always keeps.
* Default: true.

dir = <path>
* Directory for the disk cache when enabled = true. Env vars in the path
* ($SPLUNK_HOME, $HOME, …) are expanded.
* To turn the cache off use enabled = false — do not set dir = "" (an
* empty value is taken literally; surrounding quotes are not stripped).
* Default: $SPLUNK_HOME/var/run/os_k8s_search/cache.

discovery_ttl = <duration>
* Disk-cache TTL for API discovery responses. Discovery is
* schema, not state — long TTLs are safe. Matches kubectl's
* default. 0 disables disk caching of discovery (the in-memory
* 5-min cache still applies).
* Default: 10m.

list_default_ttl = <duration>
* Default TTL for LIST operations when
* an SPL `cache=` param is absent. Applies to `| k8s
* kind=<plural>` and `| k8sevents`. `| k8slogs` deliberately
* ignores this default and uses cache=0 for its pod-enumeration
* step (live-logs expectation). Set to 0 to disable LIST
* caching globally; per-search `cache=<duration>` overrides
* either direction.
* Default: 30s.

get_default_ttl = <duration>
* Default TTL for single-object GET
* operations when an SPL `cache=` param is absent. Applies to
* `| k8sdescribe` (both the object GetItem and its events LIST)
* and `| k8s kind=<plural>/<name>`. Shorter than
* list_default_ttl because describe is often a debug-and-iterate
* workflow.
* Default: 10s.

max_size_bytes = <integer>
* Soft cap on total disk used by the cache, shared across the discovery
* and response layers. Enforced by the periodic sweep, not at write time,
* so the directory can briefly exceed the cap between sweeps (default
* cadence 5 minutes) — treat it as the steady-state footprint, not a hard
* ceiling. When exceeded, the oldest entries are evicted until it fits.
* Default: 268435456 (256 MiB).

max_entries = <integer>
* Soft cap on the number of cached entries (discovery + responses).
* Enforced by the same periodic sweep as max_size_bytes; whichever cap is
* reached first triggers eviction of the oldest entries.
* Default: 4096.

[license]
* The k8s_search product license. SHC-replicated (see server.conf) so
* every Search Head Cluster member shares one entitlement — an SHC counts
* as one installation.

key = <string>
* The signed license key from your order confirmation.
* Empty (the default) is the free tier: one registered cluster, standalone
* search head only (not a Search Head Cluster), and no per-user credentials
* or impersonation.
* A valid key raises the cluster cap and unlocks Search Head Cluster
* operation, per-user credentials, and impersonation; the allowed cluster
* and installation counts are encoded in the key.
* Prefer the setup page (which writes to local/) over editing default/.
* Default: empty (free tier).
