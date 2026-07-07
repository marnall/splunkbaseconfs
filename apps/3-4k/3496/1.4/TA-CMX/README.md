# ABOUT THIS APP

The Cisco CMX Add-on for Splunk is used to gather data from CMX devices and do field extraction. 


# REQUIREMENTS

* Splunk version >= 6.3
* If using a forwarder, it must be a HEAVY forwarder( we use the HF because the universal forwarder does not include python)
* The forwarder system must have network access (HTTP/HTTPS) to one or more CMX devices which are to be Splunked.
* Admin user ID and password for collecting data from CMX device.

* Application can work on both Windows and Linux platforms

# Recommended System configuration

* Splunk forwarder system should have 4 GB of RAM and a quad-core CPU to run this app smoothly.


# Topology and Setting up Splunk Environment

* This app has been distributed in two parts.

  1) Add-on app, which runs collector scripts and gathers data from CMX devices, does indexing on it and provides indexed data to the Main app.
  2) The main app, which receives indexed data from Add-on app, runs searches on it and builds a dashboard using indexed data.

* This App can be set up in two ways:
  1) **Standalone Mode**: Install the main app and Add-on app on a single machine.

     * Here both the app resides on a single machine.
     * The main app uses the data collected by Add-on app and builds dashboard on it

   2) **Distributed Environment**: Install the main app and Add-on app on search head, Only Add-on on forwarder system and indexes.conf file from Add-on bundle on Indexer.

     * Here also both the apps resides on search head machine, but no need to configure Add-on on search head.
     * Only Add-on needs to be installed and configured on forwarder system.
     * Execute the following command on forwarder to forward the collected data to the indexer.
       $SPLUNK_HOME/bin/splunk add forward-server <indexer_ip_address>:9997
     * On Indexer machine, enable event listening on port 9997 (recommended by Splunk).
     * Main app on search head uses the received data and builds dashboards on it.

# Installation of App

* This app can be installed through UI using "Manage Apps" or extract zip file directly into $SPLUNK_HOME/etc/apps/ folder.

*  After installation, go to the Apps->Manage Apps->Set up TA-CMX. New set up screen will open which will ask for CMX parameters, set appropriate parameters.

* Please note, if you are using a self-signed certificate, set appropriate argument on the setup page.

* The CMX setup page will ask for the index name, where data will get collected if no index is defined it will go to main index. In case you update the index, please verify the macro defination for 'cmx_index'.

# Sample Event generation
* This application bundles sample events which can be used for test purpose. To generate sample events, you will require Splunk_SA_Eventgen > 4.0.

#Custom Command
*We have developed one custom command "cmxfloorinfo" to fetch details of floor from cmxmap sourcetype. 

# OPEN SOURCE COMPONENTS AND LICENSES

* We are using splunk_http_event_collector file for adding authentication token to HTTP event for ingesting via HTTP Event Collector in SPlunk.   
https://github.com/georgestarcher/Splunk-Class-httpevent/blob/master/splunk_http_event_collector.py.

# Support
* Email support will be provided as best effort.
* CMX Connectors are supported by the CMX Cloud team at Cisco.
* Cases can be opened by sending an email to cmx-cloud-support@external.cisco.com
* Support requires a valid CMX installation and a CMX Advanced Licenses on applicable Access Points.
* Cases can be opened 24x7

# TEST YOUR INSTALL

The main app dashboard can take some time to populate the dashboards Once data collection is started. A good test to see that you are receiving all of the data we expect is to run this search after several minutes:

    search `cmx_index` | stats count by sourcetype

In particular, you should see these sourcetypes:
* cmxhttp
* cmxanalytics
* cmxactive
* cmxmap

If you don't see these sourcetypes, check log file under $SPLUNK_HOME/var/log/TA-CMX/tacmx.log.