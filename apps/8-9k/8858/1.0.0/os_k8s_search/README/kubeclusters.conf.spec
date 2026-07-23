# kubeclusters.conf.spec — schema for the system-scope cluster registry.
#
# Lives at $SPLUNK_HOME/etc/apps/os_k8s_search/local/kubeclusters.conf and
# is administered via the Kubernetes Search setup page. AppInspect
# uses this spec to validate any local/ file shipped or installed by
# an operator.
#
# All secret material (bearer tokens, client cert/key PEM) lives in
# Splunk's storage/passwords, NOT in this conf. Each *_ref field below
# names a storage/passwords entry.

[cluster.<name>]
* Defines a single Kubernetes cluster the k8s_search search commands
* can target. <name> is referenced from SPL as `context=<name>` and
* from per-user kubeauth.conf as [auth.<name>]. Use only [a-z0-9._-],
* and avoid `__` (a double underscore can alias another cluster's
* stored credentials).

server = <string>
* The Kubernetes API server URL (https://host:port). Required.
* Must not embed credentials (no user:password@host — the URL is logged
* and stored). An http:// URL is rejected unless insecure = true.

ca_data_ref = <string>
* storage/passwords realm:name for a PEM-encoded CA certificate.
* Preferred over ca_path because it keeps the cert encrypted at rest.
* Set exactly one of ca_data_ref or ca_path (not both), unless
* insecure = true.

ca_path = <string>
* Alternative to ca_data_ref: literal filesystem path to a PEM
* CA certificate. Convenient for in-cluster service-account
* defaults (/var/run/secrets/kubernetes.io/serviceaccount/ca.crt).

insecure = <bool>
* When true, skip TLS verification of the API server cert.
* Defaults to false. Use only for local dev clusters with self-signed
* certs where you cannot or will not configure ca_data_ref / ca_path.

tls_server_name = <string>
* Optional SNI / verification hostname. Use when the API server
* listens on an IP that does not appear in the cert's SAN list
* (some private-cloud / kubeadm bootstraps).

namespace = <string>
* Optional default namespace baked into the connection. SPL
* `namespace=` always wins when present.

impersonate = <bool>
* When true, switches this cluster into Kubernetes user-impersonation
* mode. The bearer credential from default_auth still authenticates
* the request; the Splunk user running the search is stamped into
* the Impersonate-User HTTP header so the API server applies per-user
* RBAC. The default_auth identity must hold the `impersonate` verb on
* `users` (typically a ClusterRole + ClusterRoleBinding).
* Per-user kubeauth.conf is intentionally ignored in this mode.
* Scheduled saved searches owned by "nobody" are refused with a
* clear error rather than impersonating an empty user.
* Defaults to false.

[default_auth.<cluster>]
* Admin-managed fallback credentials for the named cluster. Used
* when the search user has no per-user [auth.<cluster>] override
* in their kubeauth.conf.

type = token|cert
* Required. Selects which fields below are consulted.
* "token" — token_ref is required.
* "cert"  — client_cert_ref + client_key_ref are required.

token_ref = <string>
* storage/passwords realm:name for the bearer token. Required when
* type=token.

client_cert_ref = <string>
* storage/passwords realm:name for the client certificate PEM.
* Required when type=cert.

client_key_ref = <string>
* storage/passwords realm:name for the client key PEM.
* Required when type=cert.
