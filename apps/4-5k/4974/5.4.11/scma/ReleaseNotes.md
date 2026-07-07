# Version 5.2.6

# Version 5.2.5
- New: SCMA Review Beta that allows analyzing the data without the need to export/import back into Splunk.  The dashboard operates on the data contained in the _introspection index.
- New: The scma command now accepts a range of searches for the order parameter.
- New: Checks added in this release:
     - search_commands_runshellscript: The check searches for the runshellscript command in the environment.
     - search_commands_python: The check searches for Python Version 2 commands in the environment.
     - search_provisioning_lookups: The check finds scheduled jobs that generates lookup files using custom search commands.
     - indexing_sourcetype_ingestion: The check calculates the amount of ingestion by host and returns all sourcetypes that are being ingested and the amount of data being ingested in the last 7 days.
     - indexing_ingest_retention: The check calculates ingest distribution by index retention in the last 7 days.
     - indexing_compression_ratio: The check calculates the overall index compression ratio to better understand the daily ingest disk space utilization.
     - search_avg_run_time: The check provides average run time and search count statistics by product (Core, ES, ITSI).
     - indexing_summary_stats: The check provides data model and report acceleration storage size usage information, bucket count and related indexes count by indexer cluster by summary type and summary name.
     - search_index_statistics: The check provides statistical information by index. Within a 7 day period, it collects information on the number of searches, number of users, number of hosts, number of scheduled jobs number of apps, search types, search head host id names searching these indexes and the grand total runtime for each.
- Minor fixes to 2 - Checks and the troubleshooting dashboards.
- Discovery job updates.

# Version 5.2.4
- Minor fixes to 2 - Checks and the troubleshooting dashboards
- Updated the logic of the discovery job
- Bugfix: More tolerance on savedsearches format

# Version 5.2.3
- Minor bugfixes

# Version 5.2.1
- Major improvements to the SCMA Review Dashboard
- Revamped and added new checks
- Various bug fixes and performance improvements
- Legacy Dashboard Check, Object Collisions, Knowledge Object Inventory panels moved from the Environment tab to the Apps tab.
- Introduction of Rapid Application Deployer (RAD) *Beta*
     - Bulk migration of validated private applications
     - Bulk migration of supported SplunkBase applications (With selectable version)
     - Migration of local configurations and dashboards
     - Migration of local configuration for core apps (e.g., search)
     - ACL migration
- Introduction of ACS Helper *Beta* :  A simple UI in front of ACS services :
     - List, Delete Applications for a Splunk Cloud Stack
     - Configure IP allow list
     - Configure outbound ports
     - Manage Indexes
     - Manage HTTP Event Collector (HEC) tokens
     - View maintenance windows 
     - Manage restarts
