# ABOUT THIS APP

The Tenable App for Splunk builds dashboards on indexed data provided by Tenable Add-On.

# REQUIREMENTS

* [Tenable Add-on for Splunk](https://splunkbase.splunk.com/app/4060)

# COMPATIBILITY MATRIX

* Browser: Google Chrome, Mozilla Firefox
* OS: Platform independent
* Splunk Enterprise version: 9.4.x, 9.3.x, 9.2.x, 9.1.x
* Supported Splunk Deployment: Splunk Cloud, Splunk Standalone, and Distributed Deployment

# Release Notes

## Version 6.1.0
* Added "Assets Dashboard" for visualizing asset details of the following products: IO, SC, OT, WAS, ASM
* Added support for "WAS" and "OT" products in "Vulnerability Center" dashboard


## Version 6.0.5
* Added dashboard for WAS integration.


## Version 6.0.4
* Fixed JavaScript alert issue.

## Version 6.0.3
* Removed Host Audit Findings, Web Application Findings, Cloud Findings support from the application
* **Note:** It is requested to run below reports manually after upgrading Tenable add-on to 6.x.x  
	* Tenable IO Plugin Data - All Time 
	* Tenable IO Vuln Data - All Time

## Version 6.0.2

* Added support for Tenable.io Explore -> Assets (Cloud Resources, Web Applications) and Findings (Cloud Findings, Web Application Vulnerabilities)
* **Note:** It is requested to run below reports manually after upgrading Tenable add-on to 6.x.x  
	* Tenable IO Plugin Data - All Time 
	* Tenable IO Vuln Data - All Time
	* Tenable IO Cloud Vuln Data - All Time
	* Tenable IO Web App Vuln Data - All Time

## Version 5.1.0

* Used version flag for dashboards to use latest Jquery 3.5 on Splunk v8.2+

## Version: 5.0.0
* Fixed the dashboard queries to show correct vulnerability counts for large number of events (>50,000).

## Version: 2.1.0
* Made the app compatible with Python2 and Python3

## Version: 2.0.0
* Added dashboards for Tenable NNM.

## Version: 1.0.2
* Moved macros from Technology Add-On For Tenable to Tenable App For Splunk.

# Upgrade to version 2.0.0

* Delete $SPLUNK_HOME/etc/apps/TA-tenable/local/macros.conf file if exist.
* Update definition of "get_tenable_index" macro in the Tenable App For Splunk.
* Delete $SPLUNK_HOME/etc/apps/TenableAppforSplunk/local and $SPLUNK_HOME/etc/apps/TenableAppforSplunk/lookups folders and $SPLUNK_HOME/etc/apps/TenableAppforSplunk/appserver/static/dashboard.css file if exist.

# RECOMMENDED SYSTEM CONFIGURATION

* Splunk forwarder system should have 12 GB of RAM and a six-core CPU to run this Technology Add-on smoothly.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app has been distributed in two parts.

  1) Add-on app, which takes input from modular input, does indexing on it and provides indexed data to Main app.
  2) Main app, which receives indexed data from Add-on app, runs searches on it and builds dashboard using indexed data.

* This App can be set up in two ways:
  1) **Standalone Mode**: Install main app and Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup

     * Here both the app resides on a single machine.
	 * Add-on needs to be installed and configured on stand alone splunk instance.
     * Main app uses the data collected by Add-on.

   2) **Distributed Environment**: Install main app and Add-on on search head and Add-on on Heavy forwarder.

     * Here also both the apps resides on search head machine, but only account needs to be configured on search head.
     * Only Add-on needs to be installed and configured on Heavy forwarder system.
     * Execute the following command on Heavy forwarder to forward the collected data to the indexer.
       /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
     * On Indexer machine, enable event listening on port 9997 (recommended by Splunk).
     * Main app on search head uses the received data and builds dashboards on it.

# INSTALLATION OF APP

* This app can be installed through UI using "Manage Apps" or extract zip file directly into $SPLUNK_HOME/etc/apps/ folder.

# CONFIGURATION OF APP

* Earliest time for the savedsearches "Tenable IO Vuln Data" and "Tenable SC Vuln Data" should be greater than or equal to interval time used in respective inputs.
* After the successful execution of the data collection for the first time run custom commands "| rebuildvulnlookups" and "| rebuildpluginlookups" one after one by navigating to TenableAppforSplunk->Search OR run "Tenable IO Vuln Data - All Time", "Tenable SC Vuln Data - All Time" and "Tenable IO Plugin Data - All Time" savedsearches by navigating to Settings->Searches, reports, and alerts. 

* Configure Macro:
		
	* If user has selected default index in "Data Input" Configuration, then no need to perform this step.
	  But if user has given any other index in "Data Input" Configuration, then do below steps.
		* Go to Settings->Advanced search->Search macros
		* Select "Tenable" in App context
		* Click on "get_tenable_index" macro and update definition to index=INDEX_NAME, Where INDEX_NAME should be the same name given at the time of creating data input and then click Save.

# TEST YOUR INSTALL

* The main app dashboard can take some time to populate the dashboards, once data collection is started. A good test to see that you are receiving all of the data we expect is to run this search after several minutes:

	search `get_tenable_index` | stats count by sourcetype
	
In particular, you should see "tenable:io:vuln", "tenable:io:assets", "tenable:io:plugin", "tenable:sc:vuln", "tenable:sc:plugin", "tenable:sc:assets", "tenable:sc:mobile:vuln", "tenable:sc:mobile:assets", "tenable:nnm:vuln" sourcetype.

# SAVEDSEARCHES

* This application contains following saved searches, which are used in forming lookup files.
  * "Tenable SC Asset Data" - This savedsearch is used to create a lookup called "sc_asset_data_lookup" which is a KV store collection named sc_asset_data_lookup. This savedsearch runs every one hour to fill the data of the previous hour.
  * "Tenable SC Asset Data - All Time" - This savedsearch is used to create a lookup called "sc_asset_data_lookup" which is a KV store collection named sc_asset_data_lookup. This lookup is disabled by default. User can enable it and run the savedsearch in "All Time" time range to fill the lookup with all the data.
  * "Tenable SC Plugin Data" - This savedsearch is used to create a lookup called "sc_plugin_data_lookup" which is a KV store collection named sc_plugin_data_lookup.
  * "Tenable SC Vuln Data" - This savedsearch is used to create a lookup called "sc_vuln_data_lookup" which is a KV store collection named sc_vuln_data_lookup.
  * "Tenable IO Plugin Data" - This savedsearch is used to create a lookup called "io_plugin_data_lookup" which is a KV store collection named io_plugin_data_lookup.
  * "Tenable IO Asset Data" - This savedsearch is used to create a lookup called "io_asset_data_lookup" which is a KV store collection named io_asset_data_lookup. This savedsearch runs every one hour to fill the data of the previous hour.
  * "Tenable IO Asset Data - All Time" - This savedsearch is used to create a lookup called "io_asset_data_lookup" which is a KV store collection named io_asset_data_lookup. This lookup is disabled by default. User can enable it and run the savedsearch in "All Time" time range to fill the lookup with all the data.
  * "Tenable IO Vuln Data" - This savedsearch is used to create a lookup called "io_vuln_data_lookup" which is a KV store collection named io_vuln_data_lookup.
  * "Tenable NNM Vuln Data" - This savedsearch is used to create a lookup called "nnm_vuln_data_lookup" which is a KV store collection named nnm_vuln_data_lookup.
  * "NNM Events Over Time" - This savedsearch shows timechart count by plugin_name for tenable:nnm:vuln sourcetype.
  * "NNM Top 10 Events" - This savedsearch shows top 10 plugin_name for tenable:nnm:vuln sourcetype.
  * "NNM Top Destination by Country" - This savedsearch shows top 10 country based on destination for tenable:nnm:vuln sourcetype.
  * "NNM Top Source by Country" - This savedsearch shows top 10 country based on source for tenable:nnm:vuln sourcetype.
  * "Top Destination IP" - This savedsearch shows top 10 destination IP for tenable:nnm:vuln sourcetype.
  * "Top Destination Port" - This savedsearch shows top 10 destination port for tenable:nnm:vuln sourcetype.
  * "Top NNM Plugin ID" - This savedsearch shows top 10 plugin id for tenable:nnm:vuln sourcetype.
  * "Top Source IP" - This savedsearch shows top 10 source ip for tenable:nnm:vuln sourcetype.
  * "Top Source Port" - This savedsearch shows top 10 source port for tenable:nnm:vuln sourcetype.
  * "Tenable SC Vuln Data - All Time" - This savedsearch is used to rebuild the "sc_vuln_data_lookup" lookup.
  * "Tenable IO Vuln Data - All Time" - This savedsearch is used to rebuild the "io_vuln_data_lookup" lookup.
  * "Tenable IO and SC vuln Data" - This savedsearch shows IO and SC data based on io_vuln_data_lookup, sc_vuln_data_lookup. 
  * "Tenable IO Plugin Data - All Time" - This savedsearch is used to rebuild the "io_plugin_data_lookup" lookup.
  * "Tenable WAS Assets Data - All Time" - This savedsearch is used to create a lookup called "was_assets_data_lookup" which is a KV store collection named was_assets_data_lookup. This lookup is disabled by default. User can enable it and run the savedsearch in "All Time" time range to fill the lookup with all the data.
  * "Tenable ASM Assets Data - All Time" - This savedsearch is used to create a lookup called "asm_assets_data_lookup" which is a KV store collection named asm_assets_data_lookup. This lookup is disabled by default. User can enable it and run the savedsearch in "All Time" time range to fill the lookup with all the data.
  * "Tenable SC Mobile Assets - All Time" - This savedsearch is used to create a lookup called "sc_mobile_assets_data_lookup" which is a KV store collection named sc_mobile_assets_data_lookup. This lookup is disabled by default. User can enable it and run the savedsearch in "All Time" time range to fill the lookup with all the data.
  * "Tenable OT Assets - All Time" - This savedsearch is used to create a lookup called "ot_assets_data_lookup" which is a KV store collection named ot_assets_data_lookup. This lookup is disabled by default. User can enable it and run the savedsearch in "All Time" time range to fill the lookup with all the data.
  * "Tenable WAS Assets Data - Last 1 Hour" - This savedsearch is used to create a lookup called "was_assets_data_lookup" which is a KV store collection named was_assets_data_lookup. This savedsearch runs every one hour to fill the data of the previous hour and the savedsearch is enabled by default
  * "Tenable ASM Assets Data - Last 1 Hour" - This savedsearch is used to create a lookup called "asm_assets_data_lookup" which is a KV store collection named asm_assets_data_lookup. This savedsearch runs every one hour to fill the data of the previous hour and the savedsearch is enabled by default
  * "Tenable SC Mobile Assets - Last 1 Hour" - This savedsearch is used to create a lookup called "sc_mobile_assets_data_lookup" which is a KV store collection named sc_mobile_assets_data_lookup. This savedsearch runs every one hour to fill the data of the previous hour and the savedsearch is enabled by default
  * "Tenable OT Assets - Last 1 Hour" - This savedsearch is used to create a lookup called "ot_assets_data_lookup" which is a KV store collection named ot_assets_data_lookup. This savedsearch runs every one hour to fill the data of the previous hour and the savedsearch is enabled by default

## Steps to run "All Time" saved searches which are disabled by default

1. Go to Settings > **Searches, Reports, and Alerts**.
2. Find and select the saved search you want to run.
  - For this case, select the savedsearche: "Tenable WAS Assets Data - All Time"
3. Click on the "Run" button to execute the saved search.
4. Check the result of the savedsearch.
5. To ensure if the data is filled in corresponding lookup, run the command `|inputlookup was_assets_data_lookup` and see the results

User can run all the savedsearches mentioned below to populate All Time data in the kvstore lookups, which eventually populates the dashbaord
- Tenable ASM Assets Data - All Time
- Tenable SC Assets Data - All Time
- Tenable OT Assets - All Time
- Tenable SC Asset Data - All Time
- Tenable IO Asset Data - All Time

# TROUBLESHOOTING

* If you do not see any results in search:
	* Go to the macro defined from Settings->Advanced search->Search macros
	* Click on "get_tenable_index" macro.
	* Check if the index name matches with the index defined in the "Data Input" step.

* If the problem still persists increase the Time Range filter provided on the top left corner.
* If you find inconsistency in "Vulnerability Center" dashboard, then run:
   * Custom command "| rebuildvulnlookups" by navigating to TenableAppforSplunk->Search OR run "Tenable IO Vuln Data - All Time" and "Tenable SC Vuln Data - All Time" savedsearches by navigating to Settings->Searches, reports, and alerts.
   * Custom command "| rebuildpluginlookups" by navigating to TenableAppforSplunk->Search OR run "Tenable IO Plugin Data - All Time" savedsearch by navigating to Settings->Searches, reports, and alerts.
* You can see the log of custom command "| rebuildvulnlookups" in the file $SPLUNK_HOME/var/log/splunk/tenable_rebuild_vuln_lookup.log.
* You can see the log of custom command "| rebuildpluginlookups" in the file $SPLUNK_HOME/var/log/splunk/tenable_rebuild_plugin_lookup.log.

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/TenableAppforSplunk
* Remove $SPLUNK_HOME/var/log/splunk/**tenable_rebuild_vuln_lookup.log**
* Remove $SPLUNK_HOME/var/log/splunk/**tenable_rebuild_plugin_lookup.log**
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# SUPPORT
* Support Offered: Yes
* Support Email: support@tenable.com

### Copyright 2025 Tenable, Inc.
