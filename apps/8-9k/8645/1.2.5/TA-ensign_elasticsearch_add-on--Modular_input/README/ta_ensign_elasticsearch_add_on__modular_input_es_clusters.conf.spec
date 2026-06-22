[<name>]
es_host = <string> The Elasticsearch Host IP Address or Domain. Supports comma-separated values for multi-node clusters (e.g., "node1.es.local, node2.es.local, node3.es.local").
es_port = <integer> The Elasticsearch Port (e.g., 9200).
es_user = <string> The Elasticsearch Username.
es_pass = <string> The Elasticsearch Password.
verify_cert = <bool> Enable or Disable SSL/TLS certificate verification. 1 for Yes, 0 for No.
cert_location = <string> The absolute path to the CA Certificate file. Required if verify_cert is 1.
enable_sniffing = <bool> Enable Elasticsearch node sniffing/auto-discovery. When enabled, the client will automatically discover and connect to all available nodes in the cluster via the ES _nodes API. 1 for Yes, 0 for No. Default: 0.
max_retries = <integer> Maximum number of retry attempts when a connection to an Elasticsearch node fails. Default: 3.
retry_on_timeout = <bool> Enable automatic retry when a connection to Elasticsearch times out. 1 for Yes, 0 for No. Default: 1.
connection_timeout = <integer> Connection timeout in seconds for Elasticsearch requests. Default: 30.
