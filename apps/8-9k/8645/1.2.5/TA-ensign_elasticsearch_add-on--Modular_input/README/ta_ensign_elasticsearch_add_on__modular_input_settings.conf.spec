[proxy]
proxy_enabled = 
proxy_type = 
proxy_url = 
proxy_port = 
proxy_username = 
proxy_password = 
proxy_rdns = 

[logging]
loglevel = 

[checkpoint]
checkpoint_storage = <string> Checkpoint storage backend. Valid values: file, kvstore. When set to kvstore, checkpoints are stored in Splunk KVStore (SHC-native replication). Smart Fallback reads both backends on startup and uses the most recent bookmark. Default: file.