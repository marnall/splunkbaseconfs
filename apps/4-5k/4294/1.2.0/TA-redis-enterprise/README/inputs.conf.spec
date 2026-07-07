[cluster_stats://<name>]
account = Account to use to access the Redis Enterprise REST API
protocol = 
fqdn = FQDN for Redis Enterprise cluster
port = Port for the Redis Enterprise REST API
stats_interval = Time interval for which to get stats
stime = Initial value of the checkpoint variable
builtin_system_checkpoint_storage_type = 

[bdb_alerts://<name>]
account = Account to use to access the Redis Enterprise REST API
protocol = 
fqdn = FQDN for Redis Enterprise cluster
port = Port for the Redis Enterprise REST API
bdb = ID of the BDB to get stats for

[node_alerts://<name>]
account = Account to use to access the Redis Enterprise REST API
protocol = 
fqdn = FQDN for Redis Enterprise cluster
port = Port for the Redis Enterprise REST API
node = ID of the node to get alert states for

[bdb_stats://<name>]
account = Account to use to access the Redis Enterprise REST API
protocol = 
fqdn = FQDN for Redis Enterprise cluster
port = Port for the Redis Enterprise REST API
bdb = Id of the BDB to get stats for
stats_interval = time interval for which to get stats
stime = Initial value of the checkpoint variable
builtin_system_checkpoint_storage_type = 

[cluster_alerts://<name>]
account = Account to use to access the Redis Enterprise REST API
protocol = 
fqdn = FQDN for Redis Enterprise cluster
port = Port for the Redis Enterprise REST API

[logs://<name>]
account = 
protocol = 
fqdn = FQDN for Redis Enterprise cluster
port = Port for the Redis Enterprise REST API
stime = Initial value of the checkpoint variable
builtin_system_checkpoint_storage_type = 

[cluster_info://<name>]
account = 
protocol = 
fqdn = FQDN for Redis Enterprise cluster
port = Port for the Redis Enterprise REST API

[node_info://<name>]
account = 
protocol = 
fqdn = FQDN for Redis Enterprise cluster
port = Port for the Redis Enterprise REST API
node = ID of the node to get info for

[bdb_info://<name>]
account = 
protocol = 
fqdn = FQDN for Redis Enterprise cluster
port = Port for the Redis Enterprise REST API
bdb = ID of the BDB to get info for

[node_stats://<name>]
account = Account to use to access the Redis Enterprise REST API
protocol = 
fqdn = FQDN for Redis Enterprise cluster
port = Port for the Redis Enterprise REST API
node = ID of the node for which to get stats
stats_interval = Time interval for which to get stats
stime = Initial value of the checkpoint variable
builtin_system_checkpoint_storage_type =