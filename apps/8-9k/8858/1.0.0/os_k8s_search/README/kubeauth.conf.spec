# kubeauth.conf.spec — per-user credential override schema.
#
# Lives at $SPLUNK_HOME/etc/users/<user>/os_k8s_search/local/kubeauth.conf
# (user scope) and is written by the setup page when an individual
# user overrides the admin's default cluster credentials.
#
# An [auth.<cluster>] stanza in this file takes precedence over the
# matching [default_auth.<cluster>] in the system-scope
# kubeclusters.conf at search time. <cluster> is the name from
# [cluster.<name>] in kubeclusters.conf.
#
# All secret material is stored in storage/passwords via *_ref
# fields; this file never contains the credentials themselves.

[auth.<cluster>]
* Per-user credentials for the named cluster.

type = token|cert
* Required. Selects which fields below are consulted, with the same
* semantics as kubeclusters.conf [default_auth.<cluster>]: "token" needs
* token_ref; "cert" needs client_cert_ref + client_key_ref.

token_ref = <string>
* storage/passwords realm:name for the bearer token. Required when type=token.

client_cert_ref = <string>
* storage/passwords realm:name for the client certificate PEM.
* Required when type=cert.

client_key_ref = <string>
* storage/passwords realm:name for the client key PEM.
* Required when type=cert.
