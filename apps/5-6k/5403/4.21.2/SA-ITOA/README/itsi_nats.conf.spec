# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
# This file contains attributes and values for configuring the IT Service
# Intelligence (ITSI) app.
#
# There is an itsi_nats.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place an itsi_nats.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local/. You must restart Splunk software to enable
# configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles
#
# CAUTION: You can drastically affect your Splunk installation by changing these settings.
# Consult technical support (http://www.splunk.com/page/submit_issue) if you are not sure how
# to configure this file.

####
# GLOBAL SETTINGS
####
# Use the [default] stanza to define any global settings.
#  * You can also define global settings outside of any stanza, at the top
#    of the file.
#  * Each .conf file should have at most one default stanza. If there are
#    multiple default stanzas, attributes are combined. In the case of
#    multiple definitions of the same attribute, the last definition in the
#    file wins.
#  * If an attribute is defined at both the global level and in a specific
#    stanza, the value in the specific stanza takes precedence.

[nats_settings]
* Defines settings related to ITSI NATS implementation.

job_queue_timeout = <seconds>
* The amount of time, in seconds, before the backup/restore job queue
  times out if the node owning the job has been down for too long to
  allow other jobs to proceed.
* The minimum supported timeout period is 3600 seconds (1 hour). The system
  sets the timeout to 3600 seconds when a value lower than this is set.
* Default: 43200 (12 hours)

require_tls_client_cert_cloud = <boolean>
* Whether tls setting is required while connecting to NATS server in cloud deployment.
* If "0", NAT server is connected without tls certificate.
* If "1", NAT server is connected with tls certificate.
* Default: 1

require_tls_client_cert_on_prem = <boolean>
* Whether tls setting is required while connecting to NATS server in on-prem deployment.
* If "0", NAT server is connected without tls certificate.
* If "1", NAT server is connected with tls certificate.
* Default: 0

require_auth = <boolean>
* Whether authentication is required while connecting to NATS server.
* If "0", NAT server is connected without authentication.
* If "1", NAT server is connected with authentication.
* Default: 0

nats_servers = <string>
* A comma separated list of urls used to connect to nats server.
* Default: nats://127.0.0.1:4222

nats_server_connect_time = <integer>
* Limit how long it can take to establish a connection to a server.
* Default: 5 seconds

nats_max_reconnect_attempts = <integer>
* The maximum reconnect attempts per server. Once reconnect to a server fails the specified
* amount of times in a row, it will be removed from the connect list.
* Default: 3

nats_reconnect_time_wait = <integer>
* A wait setting to prevent to connect to the same server over and over.
* This makes sure that between two reconnect attempts to the same server at least a certain amount of time has passed.
* Default: 5 seconds

retention_max_age = <integer>
* The maximum age of any message in the stream, expressed in seconds.
* Messages older than this will be removed from the stream.
* Default: 3600 seconds

max_memory_store = <integer>
* Maximum memory storage that can be allocated to JetStream in bytes.
* Default: 1073741824 bytes

max_file_store = <integer>
* Maximum file storage that can be allocated to JetStream in bytes.
* Default: 53687091200 bytes

max_buffered_msgs = <integer>
* The maximum number of messages that can be queued for each stream before the rate limit is hit.
* Default: 100000

max_buffered_size = <integer>
* The maximum size (in bytes) for messages that can be queued for each stream before the rate limit is hit.
* Default: 268435456

pulse_frequency = 60
* The value, in seconds, to wait before checking if a license exists, or a migration is pending.
* Default: 60 seconds

require_license = 1
* If set to "1", the system checks that a license exists before starting the NATS Server and Queue modes.
* Default: 1

require_migration_completed_check = 1
* If set to "1", the system requires that migration is complete before starting NATS Server and Queue mode.
* Default: 1

stream_replication_factor = 3
* This setting determines how many locations (streams) to store incoming events from the queue distribution system.
* The average setting to continue operating during outages is a file-based stream with this setting set to "3".
* In single instance, this setting is set to "1". In a search head cluster environment, it is set to "3" by default.

require_nats_metrics = 1
* If set to "1", the system requires ingested NATS metrics to monitor the NATS queue.
* Default: 1

nats_fips_activated = 1
* This setting ensures that the NATS server is FIPS compatible.
* If set to "1", the NATS server will be FIPS compliant.

max_retry_jet_stream_creation = 5
* Number of times system will attempt to create a stream in case of jetstream creation failure
* Default: 5

jetstream_creation_retry_wait_time = 60
* The value, in seconds, to wait before retrying to create a jet stream

nats_auto_discover_publisher_nodes = 1
* If set to "1", the system automatically identifies all the nodes to push the events in SHC.

monitoring_endpoint_configs = <array>
* array of nats monitoring endpoints with respective source types in events

tls_cert_san_additional_dns = <string>
* A comma separated list of any additional DNS to be used while creating TLS certificates.
* Default: localhost

tls_cert_san_additional_ip = <string>
* A comma separated list of any additional IP addresses to be used while creating TLS certificates.
* Default: 127.0.0.1

skip_check_process = <boolean>
* if true skips check process method in command_change_rules_engine_process.py file
* The check_process method verifies whether the queue mode or ad-hoc search is already enabled, ensuring that the same code is not executed again to enable the scripted input.
* Default: 1

enable_nats_route_monitor = <boolean>
* Whether or not to enable NATS route monitor.
* Default: 0
nats_route_monitor_interval = <integer>
* The interval, in seconds, at which the system checks the status of the NATS route.
* Default: 600
nats_unreachable_route_retention_max_age = <integer>
* The maximum age of unreachable route after which it will be removed from the system.
* Default: 3600