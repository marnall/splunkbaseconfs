#
# server.conf.spec — SHC replication settings for Whisper Security TA
#
# This file documents the settings in server.conf that control Search
# Head Cluster (SHC) replication for custom configuration files.
#
# Standard Splunk configuration files (transforms.conf, props.conf, etc.)
# are auto-replicated. Only custom-named files need explicit entries.
#

[shclustering]
conf_replication_include.restmap_custom = <bool>
* Whether to replicate restmap_custom.conf across SHC members.
* Default: true

conf_replication_include.ta_whisper_graph_settings = <bool>
* Whether to replicate ta_whisper_graph_settings.conf across SHC members.
* Default: true

conf_replication_include.ta_whisper_graph_account = <bool>
* Whether to replicate ta_whisper_graph_account.conf across SHC members.
* Default: true

conf_replication_include.web_custom = <bool>
* Whether to replicate web_custom.conf across SHC members.
* Default: true

conf_replication_include.authorize = <bool>
* Whether to replicate authorize.conf across SHC members.
* Default: true
