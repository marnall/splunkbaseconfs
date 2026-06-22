[nats_subscribe://<name>]
account = Account to use for this input.
index = (Default: default)
sourcetype = Source type for events collected from NATS (Default: nats:message)
subject = NATS subject to subscribe to (supports wildcards like *.events or foo.>) (Default: *)

[nats_kv://<name>]
account = Account to use for this input.
bucket = NATS JetStream KV bucket name
index = (Default: default)
sourcetype = Source type for events collected from NATS KV (Default: nats:kv)
subject = NATS JetStream KV subject pattern to watch (supports wildcards like *.events or foo.>) (Default: *)
