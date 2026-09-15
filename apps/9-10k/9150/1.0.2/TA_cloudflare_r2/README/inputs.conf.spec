[cloudflare_r2://<name>]
account = The Cloudflare R2 account (credentials) to use for this input.
bucket_name = Name of the R2 bucket containing Cloudflare Logpush files.
index = Default: default
interval = How often to poll R2 for new files, in seconds.  Default: 300
key_prefix = Limit processing to keys under this prefix, e.g. gateway_dns/ or http_requests/. Leave blank for all objects.
lookback_days = How far back to scan R2 on each poll (bounds the list). New files are deduped against a KV Store processed-key set. Widen if Logpush late-delivers batches.  Default: 1
sourcetype = Splunk sourcetype for emitted events. Match the Cloudflare App for Splunk (4501) sourcetypes where applicable (e.g. cloudflare:json, cloudflare:dns).  Default: cloudflare:json
