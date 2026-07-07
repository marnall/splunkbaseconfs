# ABOUT THIS APP

The Violin Systems FSP App for Splunk runs searches on indexed data and build dashboards using it.

# REQUIREMENTS

* Splunk version 6.5.x and 6.6.x


# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app has been distributed in two parts.

  1) Add-on app, which runs collector scripts and gathers data from Violin FSP, does indexing on it and provides indexed data to Main app.
  2) Main app, which receives indexed data from Add-on app, runs searches on it and builds dashboard using indexed data.

* This App can be set up in two ways:
  1) **Standalone Mode**: Install main app and Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup

     * Here both the app resides on a single machine.
	 * Add-on needs to be installed on Concerto's Universal forwarder and start forwarding data to stand alone splunk server.
     * Main app uses the data collected by Add-on.

   2) **Distributed Environment**: Install main app and Add-on  on search head and Add-on on Heavy forwarder (for REST API) and universal forwarder (for log collection).

     * Here also both the apps resides on search head machine, but no need to configure Add-on on search head.
     * Only Add-on needs to be installed and configured on Heavy forwarder system and universal forwarder.
     * Execute the following command on Heavy forwarder to forward the collected data to the indexer.
       /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
     * On Indexer machine, enable event listening on port 9997 (recommended by Splunk).
     * Main app on search head uses the received data and builds dashboards on it.

# INSTALLATION OF APP

* This app can be installed through UI using "Manage Apps" or extract zip file directly into $SPLUNK_HOME/etc/apps/ folder.

# TEST YOUR INSTALL

The main app dashboard can take some time to populate the dashboards, once data collection is started. A good test to see that you are receiving all of the data we expect is to run this search after several minutes:

    search `get_vm_index` | stats count by sourcetype

In particular, you should see these sourcetypes:
* violin:fsp:rest
* violin:fsp:mglogs
* violin:fsp:acmlogs

If you don't see these sourcetypes, have a look at the messages for "violin:fsp:rest" .User can see logs at $SPLUNK_HOME/var/log/violin/violin_fsp.log file.
  
# TROUBLESHOOTING

* Environment variable SPLUNK_HOME must be set
* To troubleshoot Violin FSP application, check $SPLUNK_HOME/var/log/violin/violin_fsp.log file.

# SUPPORT
* Support Offered: Yes
* Support Email: support@vmem.com
* Please visit https://www.violin-systems.com/services/support-services, and ask your question regarding Violin FSP App For Splunk, and your question will be attended to.

# SAVEDSEARCHES

This application contains following eight saved searches, which are used in the dashboard. 

* VMEM_FSP_Mapping
This saved search is used to populate "FSP_MappingLookup" lookup

* VMEM_LUN_Mapping
This saved search is used to populate "LUN_MappingLookup" lookup

* VMEM_Client_LUN_Mapping
This saved search is used to populate "LUN_Client_mapping" lookup

* VMEM_TimeMark_Mapping
This saved search is used to populate "TimeMarkLookup" lookup

* VMEM_client_summary
This saved search is used to get san client data

* VMEM_lun_summary
This saved search is used to get lun data

* VMEM_storagepool_summary
This saved search is used to get storage pool data

* VMEM_snapshot_summary
This saved search is used to get snapshot data



