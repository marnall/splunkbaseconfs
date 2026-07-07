# ABOUT THIS APP

The Cisco Network Assurance Engine (NAE) app for Splunk Enterprise is used to build dashboards on indexed data provided by "Cisco Network Assurance Engine Add-on for Splunk Enterprise" app

This app delivers centralized, real-time visibility for smart events from NAE to analyze and inspect issues in your data center fabric along with historical correlations between events in epochs to show how a particular smart event behaves over time

# REQUIREMENTS

* Splunk version supported 7.1, 7.2, 7.3 and 8.0
* This main App requires "Cisco Network Assurance Engine Add-on for Splunk Enterprise" version 2.5.0

# Recommended System configuration

* Splunk search head system should have 16 GB of RAM and a octa-core CPU to run this app smoothly.


# Topology and Setting up Splunk Environment
  
  Install main app (Cisco NAE App for Splunk Enterprise) and Add-on app (Cisco NAE Add-on for Splunk Enterprise) on a single machine.
* Here both the app resides on a single machine.
* Main app uses the data collected by Add-on app and builds dashboard on it

 Install  Main app and Add-on app on a distributed environment.
	Main app uses the data collected by Add-on app and builds dashboard on it.
	1. Install and configure the Add-on into the Heavy forwarder or one of the Indexer
        2. Install the Main app into the Search Head or Search Head cluster

# Installation of App

* This app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.
* Restart Splunk.
* Login to Splunk: http://<your_splunk_host:port>
* Open browser: http://<your_splunk_host:port>/en-US/debug/refresh. Click "Refresh"
* Open browser: http://<your_splunk_host:port>/en-US/_bump 
    (To pull all updated web resources from the server to the browser, to modify the cached items such as js, cookies, images etc..)
* Restart Splunk

* Note: 
  1) If the previous version of App is already installed, remove the cisco-app-candid folder from Splunk app folder before installation of newer version.
  2) If in case cleaned Splunk eventdata, please make sure to delete the 3 files ending with last_pull_epoch_time.txt from TA_cisco-candid/bin/ folder.
         These files are saving timestamp to get only incremental data from APIC.

# Installation of Add-on
* This Add-on app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.
* Ref documentation provided by "Cisco NAE Add-on for Splunk Enterprise" for Configuration of Add-on

* Note: If the previous version of Add-on app is already installed, remove the TA_cisco-candid folder from Splunk app folder before installation of newer version.

# Upgradation of App/Add-on
  Please disable all the scripted inputs before upgrading Add-on(TA_cisco-candid).
* Download the App package
* From the UI navigate to `Apps->Manage Apps`
* In the top right corner select "Install app from file"
* Select "Choose File" and select the App package 
* Check Upgrade App
* Select "Upload" and follow the prompts.
  #### OR
* If newer version is available on splunkbase, then App/Add-on can be updated from UI also.
  * From the UI navigate to `Apps->Manage Apps` OR click on gear icon
  * Search for Cisco NAE App/Add-on
  * Click on `'Update to <version>'` under Version Column.

# Post upgradation steps
####  Upgrading the Add-on(TA_cisco-candid) to v2.4.0 from any version

Please follow the below steps.

* If you have add-on installed in Windows enviornment and there is last_pull_epoch_time.txt file under TA_cisco-candid/local folder, then perform following steps.
  * Check permission of last_pull_epoch_time.txt file: 
    * Right Click on local/last_pull_epoch_time.txt.
    * Navigate to Properties -> Security.
    * Check the permission for SYSTEM.
  * If there is no permission for SYSTEM then follow below steps:
    * If scripted input is already enabled then first disable it.
    * Right Click on local/last_pull_epoch_time.txt.
    * Navigate to Properties -> Security.
    * Click on Edit button.
    * Click on Add button.
    * Enter <b> SYSTEM </b> in <em> Enter the object names to select </em> box.
    * Click Check Names.
    * Click on OK button (in the new window prompted by check names).
    * Again, click on OK button (in window where you entered SYSTEM).
    * Under <em> Permissions for SYSTEM </em> allow it Full Control.
    * Click on OK button (in window where you are giving permission).
    * Again, click on OK button.
    * Restart splunk
    * Enable the scripted input.

# Uninstallation of App

  This section provides the steps to uninstall App from a standalone Splunk platform installation.

  * (Optional) If you want to remove data from Splunk database, you can use the below Splunk CLI clean command to remove indexed data from an app before deleting the app.
    * $SPLUNK_HOME/bin/splunk clean eventdata -index <index_name>

  * Delete the app and its directory. The app and its directory are typically located in the folder$SPLUNK_HOME/etc/apps/<appname> or run the following command in the CLI:
    * $SPLUNK_HOME/bin/splunk remove app [appname] -auth <splunk username>:<splunk password>

  * You may need to remove user-specific directories created for your app by deleting any files found here: $SPLUNK_HOME/bin/etc/users/*/<appname>

  * Restart the Splunk platform.You can navigate to Settings -> Server controls and click the restart button in splunk web UI or use the following splunk CLI command to restart splunk:
    * $SPLUNK_HOME/bin/splunk restart

# TEST YOUR INSTALL

* Once  Add-on app  is configured to receive data from CNAE, The main app dashboard can take some time before the data is populated in all panels. A good test to see that you are receiving all of the data is to run this search after several minutes:

    index="[your index]" or "main" | stats count by sourcetype

In particular, you should see this sourcetype:
* cisco:candid:events

If you don't see these sourcetypes, have a look at the messages output by the scripted input: collect.py. Here is a sample search that will show them:

  index=_internal component="ExecProcessor" collectCandid.py "CNAE Error:" | table _time host log_level message


# Troubleshooting

* Q. Fabric dropdown is not populating with Fabric Names.
  * Run below search in All Time to populate the lookup with all fabrics.

    sourcetype="cisco:candid:events" component=smart_event_details cnae_host=* fab_id=* | dedup fab_id | table cnae_host, fab_id, fabric_settings_dto.unique_name | rename cnae_host AS "NAE Host" fab_id AS "Fabric ID" fabric_settings_dto.unique_name AS "Unique Name" | inputlookup append=T FabricIdMapping | dedup "Fabric ID" | outputlookup FabricIdMapping


# Additional Features

In addition to out-of-the-box reporting and analytics capabilities for your CNAE environment, the app includes a set of pre-defined dashboards for specific use cases:

* Home: The starting reference with a high-level overall view of smart events and epochs.

* Smart Event Statistics: Graphical representation of events that are New, Persisted, Unresolved and Resolved

* Smart Event Summary: Information of events that are New, Persisted, Unresolved and Resolved based on filters like epochs, time-range, severity, etc.

* Smart Event Analysis: Epoch Delta (changes of events between two epochs), Event Diff (Comparing two events based on hash-keys), Smart Event Lifecycle and User Assignment.

* Search: Search smart events (search the smart events based on defined filters) and Search (search bar to view events ingested in Splunk).

* Affected Object Analysis: Detailed analysis of affected objects (categorized per ACI constructs).

* Work flow Action: The app provides a workflow actions "CNAE Event Details Viewer" and "Go to Smart Event Details" on the "Search Smart Events" and "Search" Dashboards that enables user to inspect an event in further detail

# The list of open source components used in developing the App
* JsonPickle
	Splunk Web Framework Toolkit - Version 2.0
	Built by Splunk.
	https://splunkbase.splunk.com/app/1613/

# Support

* This app is supported by Cisco Systems.
* Email support during weekday business hours. Please ask question or send an email to cisco-dcn-splunk-app-owners@cisco.com 

# Release Notes

* Version 2.5.0:
  * Added two dashboards
    * Smart Event Lifecycle
    * User Assignment
  * Minor Bugfixes

* Version 2.4.0:
  * Minor Bugfixes

* Version 2.3.0:
  * Added support of Splunk 8.x

* Version 2.2.0:
  * Minor Bugfixes

* Version 2.1.0:
  * Fixed query for panel Informational Events single value
