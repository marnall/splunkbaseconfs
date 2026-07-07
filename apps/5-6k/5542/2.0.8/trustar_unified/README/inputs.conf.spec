[trustar_observables_to_kvstores://<name>]
global_account = 
enclave_ids = A comma separated list of IDs of enclaves to pull from.
ioc_types = The list of observable types to pull.
tags = A comma-separated list of tag names. Splunk will only download indicators that have ALL of these tags.
expiration_days = Observables older than this will be expired from kvstores.