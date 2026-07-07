# NetApp SANtricity App for Splunk

# ABOUT THIS APP

* NetApp SANtricity Performance App for Splunk Enterprise provides visibility into the performance and health of NetApp E-Series and EF-Series storage systems.
* Author - sowings@splunk.com
* Version - 3.1.0

# COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox, Safari
* OS: Platform Independent
* Splunk Enterprise version: 8.2.x and 8.1.x
* Supported Web Services Proxy version: <=5.1
* Supported Controller Firmware version: 8.70.2, >=08.30.20.xx, 11.30.20.xx
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

# REQUIREMENTS

* `NetApp SANtricity Add-on for Splunk` should be installed.

# RELEASE NOTES

## Version 3.1.0
* Bundled jQuery in app package and upgraded its version to v3.5.0
* Updated dashboard version to 1.1

# RECOMMENDED SYSTEM CONFIGURATION

* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app has been distributed in two parts.

    * Add-on app, which takes input from modular input, does indexing on it and provides indexed data to Main app.
    * Main app, which receives indexed data from Add-on app, runs searches on it and builds dashboard using indexed data.

* This App can be set up in two ways:
    * **Standalone Mode**: 
        * Install main app and Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup
        * Here both the app resides on a single machine.
	      * Add-on needs to be installed and configured on stand alone splunk instance.
        * Main app uses the data collected by Add-on.

    * **Distributed Environment**:
        * Install main app and Add-on on search head and Add-on on Heavy forwarder.
        * Here also both the apps resides on search head machine.
        * Only Add-on needs to be installed and configured on Heavy forwarder system.
        * Execute the following command on Heavy forwarder to forward the collected data to the indexer.
            * /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
        * On Indexer machine, enable event listening on port 9997 (recommended by Splunk).
        * Main app on search head uses the received data and builds dashboards on it.

# INSTALLATION OF APP

* Follow the below-listed steps to install an Add-on from the bundle:
    * Download the App package.
    * From the UI navigate to Apps->Manage Apps.
    * In the top right corner select Install app from file.
    * Select Choose File and select the App package.
    * Select Upload and follow the prompts.

OR

* Directly from the Find More Apps section provided in Splunk Home Dashboard.

# CONFIGURATION OF APP

* Configure Macro:
		
	* If user has selected eseries index in "Data Input" Configuration, then no need to perform this step.
	  But if user has given any other index in "Data Input" Configuration, then do below steps.
		* Go to Settings->Advanced search->Search macros
		* Select "TA-netapp_eseries" in App context
		* Click on "get_nesa_index" macro and update definition to index=INDEX_NAME, Where INDEX_NAME should be the same name given at the time of creating data input and then click Save. If data of different inputs are stored in differrnt indexes then user has to update the macro as follows; (index="INDEX_1" OR index="INDEX_2" OR index="INDEX_3"...).

# UPGRADE
## From v3.0.0 to v3.1.0
### Follow the below steps when upgrading netapp_app_eseries_perf from 3.0.0 to 3.1.0

* From the UI navigate to Apps->Manage Apps.
* In the top right corner select Install app from file.
* Select Choose File and select the App package.
* Check the upgrade option.
* Select Upload and follow the prompts.
* Restart Splunk if required and if prompted by Splunk.

# TEST YOUR INSTALL

* The main app dashboard can take some time to populate the dashboards, once data collection is started. A good test to see that you are receiving all of the data we expect is to run this search after several minutes:

	search `get_nesa_index` | stats count by sourcetype
	
In particular, you should see "eseries:graph", "eseries:drive-stats", "eseries:volume-stats", "eseries:controller-stats", "eseries:interface-stats", "eseries:mel-events", "eseries:webproxy" sourcetypes. "eseries:failures" sourcetype may not be present depending on the data.

# KEY FEATURES

1. Configuration summary provides summary configuration and status information for all arrays (storage systems) that are being monitored. Select a storage system to see detailed information on volume groups, disk pools, volumes, and assigned and unassigned drives. Further information for a volume group or disk pool can be viewed included allocated/unallocated capacity.
	
2. Performance dashboard shows performance data for a selected array, with the ability to drill down all the way to the drives. It provides Read/Write throughput, Read/Write IOPS, and Read/Write latency for Controllers, Interfaces, Volume Groups and Pools, Volumes, and Drives.
	
3. Event dashboard displays the event log maintained by the storage system.
	
4. Configuration->Hierarchical drives view dashboard and Configuration->Hierarchical volumes view dashbaord showcase the parent-child relationships for following in bubble chart format
	
	* Array, controller, volume groups/pools and volumes
	* Array, volume groups/pools and disk drives
		
	It provides zoom in/zoom out and mouse hover functionality for better readability
	
5. View cache hits data provided on cache hit dashboard to view cache effectiveness.
	
6. Hierarchy View dashboard is providing folder structure view for all arrays with its parent folders or sub folders. User can drill down from the root folder all the way up to controller and see the health of the controller.

# SAVEDSEARCHES

* This application contains following saved searches, which are used in forming lookup files.
    * "Update Controller Map" - This savedsearch is used to create a lookup called "nesa_controllers" at $SPLUNK_HOME/etc/apps/netapp_app_eseries_perf/lookups in form of csv.
    * "Update Volume Groups/Pools Map" - This savedsearch is used to create a lookup called "nesa_volume_groups" at $SPLUNK_HOME/etc/apps/netapp_app_eseries_perf/lookups in form of csv.
    * "Update Component Map" - This savedsearch is used to create a lookup called "nesa_volume_groups_component" at $SPLUNK_HOME/etc/apps/netapp_app_eseries_perf/lookups in form of csv.
    * "Update Volume Map" - This savedsearch is used to create a lookup called "nesa_volumes" at $SPLUNK_HOME/etc/apps/netapp_app_eseries_perf/lookups in form of csv.
    * "Update Drive Map" - This savedsearch is used to create a lookup called "nesa_drives" at $SPLUNK_HOME/etc/apps/netapp_app_eseries_perf/lookups in form of csv.
    * "Update Array StorageDevices Map" - This savedsearch is used to create a lookup called "nesa_folderid" at $SPLUNK_HOME/etc/apps/netapp_app_eseries_perf/lookups in form of csv.
    * There is a static lookup file called "nesa_compatibility_matrix" with file located at $SPLUNK_HOME/etc/apps/netapp_app_eseries_perf/lookups in form of csv.

# TROUBLESHOOTING

* If you do not see any results in search: 
	  * Go to the macro defined from Settings->Advanced search->Search macros
	  * Click on "get_nesa_index" macro.
	  * Check if the index name matches with the index defined in the "Data Input" step.

* If the problem still persists increase the Time Range filter provided on the top left corner.

# UNINSTALL ADD-ON
To uninstall the add-on, the user can follow the below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the netapp_app_eseries_perf folder from apps directory -> Restart Splunk.

# OPEN SOURCE COMPONENTS AND LICENSES
* Some of the components included in NetApp SANtricity App for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* Underscore JS
    * version: 1.6.0
    * URL: http://underscorejs.org
    * LICENSE: https://github.com/jashkenas/underscore/blob/master/LICENSE

* jQuery
    * version: 3.5.0
    * URL: https://jquery.com
    * LICENSE: https://github.com/jquery/jquery/blob/main/LICENSE.txt

# END USER LICENSE AGREEMENT
https://gist.githubusercontent.com/anonymous/1ae065622106feee4c6b/raw/69d761818b8e0155f92c29cc7959e6d0b1b6b567/gistfile1.txt

# SUPPORT

* Support Offered: Yes [Community Supported](https://community.netapp.com/)

### Copyright (C) 2022 NetApp
