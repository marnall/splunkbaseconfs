# ABOUT THIS APP

The Cisco CMX App for Splunk runs searches on indexed data and builds dashboards using it. It provides different dashboards to get insight into CMX data.


# REQUIREMENTS

* Splunk version >= 6.3
# Recommended System configuration

* Splunk forwarder system should have 4 GB of RAM and a quad-core CPU to run this app smoothly.

* Application can work on both Windows and Linux platforms.

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
     * The main app on search head uses the received data and builds dashboards on it.

# Installation of App

* Prerequisite
- Please ensure that TA-CMX is already installed and configured before installing this application.

* This app can be installed through UI using "Manage Apps" or extract zip file directly into $SPLUNK_HOME/etc/apps/ folder.
* We have to setup the RESTSERVER IP, port, username and password to fetch image from the server for "Floor Activity Map" dashboard - (Optional Process)

# External Data Source
* This application fetches floor images from CMX device via REST API.

# OPEN SOURCE COMPONENTS AND LICENSES

* Some of the components included in Cisco CMX App for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.
jQuery version 2.1.0 http://jquery.com/ (LICENSE https://github.com/jquery/jquery/blob/master/LICENSE.txt)
Underscore JS version 1.6.0 http://underscorejs.org (LICENSE https://github.com/jashkenas/underscore/blob/master/LICENSE)
Require JS version 2.1.15 http://github.com/jrburke/requirejs (LICENSE https://github.com/requirejs/requirejs/blob/master/LICENSE)
D3 JS version 3.3.5 https://github.com/d3/d3/releases (LICENSE appserver/static/components/d3/LICENSE)


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

If you don't see these sourcetypes, check out logs under $SPLUNK_HOME/var/log/CMX/ folder.

# Savedsearches
This application has following scheduled saved searches enabled for fetching specific data of CMX which is used in different dashboards.
*Get_Campus_Details
This schedule search is used to fetch Building information from CMX devices. This search populates lookup file named CampusImageLookup.
*Get_CMX_Device_Details
This schedule search is used to populate list containing CMX device names from where data is being ingested. This lookup is used in the dashboard to filter out data on basis of CMX device.