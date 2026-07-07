The Config_Analytics App is designed to index the Splunk Configuration files (conf) in both linux and windows environment.  It includes core apps split by Splunk server role: 

root (base linux app): root default and static folders sends conf changes from linux machines
ca_win (base windows app): sends conf changes from windows machines
ca_sh:  Enables the sh to parse the conf file changes indexed
ca_tool:  Includes various tools useful for troubleshooting configuration issues
ca_btool:  Includes resources to collect a btool view of the configurations from the sh and all peers

ca_sh includes Splunk dashboard files (xml), and the Splunk btool summary indexing searches for change management, dependency mapping, and environment mapping.

This app consists of three parts:  The main addon contains inputs and index-time props for deployment on every Splunk instance to be monitored.

Add config_analytics_sh to search heads for additional btool views of the configurations, dashboards, and reports.

Add ca_idx to indexers to create the indexes needed for the inputs from the main addon.

Lastly, config_analytics_win is simply the main app with the inputs renamed and replaced for the windows environment.

The addon has been tested in SH cluster and IDX cluster environments without issue.

A few other useful administrative tools have been included with this app.  Explore the dashboards, saved searches, and macros for knowledge objects which assist with field extraction qc, time qc, and index status validation.