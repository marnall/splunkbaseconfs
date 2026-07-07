Pensando Add-on for Splunk
=======================

# OVERVIEW
The Pensando Add-on for Splunk parses the firewall logs collected from the Pensando DSC platform. To visualize this data in Splunk dashboards, please install Pensando App for Splunk.

* Author - Pensando
* Version - 1.0.0
* Build - 15
* Creates Index - False
* Compatible with:
    * Splunk Enterprise version: 7.3.x and 8.0.x
    * <product version>
    * OS: Platform independent
    * Browser: Safari, Chrome and Firefox

# RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk configuration

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    
    1. Pensando Add-on for Splunk, which parses the firewall logs collected from Pensando DSC platform.
    2. Pensando App for Splunk, which adds dashboards to visualize the collected data.

* This app can be set up in two ways:
    
    1. **Standalone Mode**:
        * Install the Pensando App for Splunk and Pensando Add-on for Splunk.
        * The Pensando App for Splunk uses the data parsed by Pensando Add-on for Splunk and builds dashboards on it.
    2. **Distributed Environment**:
        * Install the Pensando App for Splunk and Pensando Add-on for Splunk on the search head. 
        * User needs to create data input on Splunk Universal/Heavy Forwarder to collect data from Pensando.
        * User needs to manually create an index on the indexer (No need to install Pensando App for Splunk or Pensando Add-on for Splunk on indexer).

# INSTALLATION
Pensando Add-on for Splunk can be installed through UI using "Manage Apps" > "Install app from file" or by extracting tarball directly into $SPLUNK_HOME/etc/apps/ folder.

# CONFIGURATION

## Configure Inputs on Splunk Forwarder Instance
The Pensando Add-on for Splunk manages inputs through TCP/UDP inputs provided by Splunk. To configure inputs:
* Login to Splunk WEB UI.
* Navigate to “Settings > Data inputs.
* Choose TCP or UDP and click New.
* In the left pane, click TCP / UDP to add an input.
* Click the TCP or UDP button to choose between a TCP or UDP input.
* In the Port field, enter a port number on which you are forwarding the logs from Pensando DSC device.
* In the Source name override field, enter a new source name to override the default source value, if necessary.
* Click Next to continue to the Input Settings page.
* Set the Source type to “pensando:dsc”.
* Set App context to “TA-Pensando”.
* Set the Host to either IP or DNS. This value will be reflected in the host field of the events. This should be the name of the machine from which the event originates.
* Set the Index that Splunk Enterprise should send data to for this input.
* Click Review.
* Click Submit once you have ensured everything is correct.

Once the input is configured, execute “index=<configured_index> sourcetype=pensando:dsc” query to validate that the events are being received.

## Configure Event Types on Splunk Search Head Instance
To use the CIM mapped fields, user first needs to configure the event type to provide the index in which the data is being collected. To configure event type:
* Navigate to Settings > Event types.
* Select “Pensando Add-on for Splunk” from the App dropdown.
* Click on pensando_idx.
* Update “index=main” with “index=<your_configured_index>” in the existing definition to use your configured index.
* Click Save.


# OPEN SOURCE COMPONENTS AND LICENSES
* None


# TROUBLESHOOTING
* To check the fields extracted by the TA, execute query "index=<your_index_name> sourcetype=pensando:dsc" in Splunk in verbose mode.

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/TA-Pensando/
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# SUPPORT
* Support Offered: Yes
* Support Email: splunkapp@pensando.io

### Copyright (C) 2017-2020 Pensando Systems Inc. All Rights Reserved.