Sophos XG Firewall Add-on For Splunk
=======================

# OVERVIEW
The Sophos XG Firewall Add-on For Splunk parses the firewall logs collected from the Sophos XG Firewall. To visualize this data in Splunk dashboards, please install Sophos App For Splunk.

* Author - Sophos
* Version - 1.0.2
* Build - 1
* Creates Index - False
* Compatible with:
    * Splunk Enterprise version: 7.3.x, 8.0.x and 8.1.x
	* Splunk CIM version: 4.18.1
    * Sophos XG Firewall version: SFOS 18.0.1 MR-1-Build396
    * OS: Platform independent
    * Browser: Safari, Chrome and Firefox

# RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk configuration

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    
    1. Sophos XG Firewall Add-on For Splunk, which parses the firewall logs collected from Sophos XG Firewall.
    2. Sophos App For Splunk, which adds dashboards to visualize the collected data.

* This app can be set up in two ways:
    
    1. **Standalone Mode**:
        * Install the Sophos App For Splunk and Sophos XG Firewall Add-on For Splunk.
        * The Sophos App For Splunk uses the data parsed by Sophos XG Firewall Add-on For Splunk and builds dashboards on it.
    2. **Distributed Environment**:
        * Install the Sophos App For Splunk and Sophos XG Firewall Add-on For Splunk on the search head. 
        * User needs to create data input on Splunk Universal/Heavy Forwarder to collect data from Sophos.
        * Install the Sophos XG Firewall Add-on For Splunk on the indexer, if you are using Universal Forwader. User needs to manually create an index on the indexer.

# INSTALLATION
Sophos XG Firewall Add-on For Splunk can be installed through UI using "Manage Apps" > "Install app from file" or by extracting tarball directly into $SPLUNK_HOME/etc/apps/ folder.

# CONFIGURATION

## Configure Inputs on Splunk Forwarder Instance
The Sophos XG Firewall Add-on For Splunk manages inputs through TCP/UDP inputs provided by Splunk. To configure inputs:
* Login to Splunk WEB UI.
* Navigate to “Settings > Data inputs.
* Choose TCP or UDP and click New.
* In the left pane, click TCP / UDP to add an input.
* Click the TCP or UDP button to choose between a TCP or UDP input.
* In the Port field, enter a port number on which you are forwarding the logs from Pensando DSC device.
* In the Source name override field, enter a new source name to override the default source value, if necessary.
* Click Next to continue to the Input Settings page.
* Set the Source type to “sophos:xg:logs” for UDP or “sophos:xg:logs:secure” if collecting logs through Secure log transmission.
* Set App context to “TA-sophos_xg_firewall”.
* Set the Host to either IP or DNS. This value will be reflected in the host field of the events. This should be the name of the machine from which the event originates.
* Set the Index that Splunk Enterprise should send data to for this input.
* Click Review.
* Click Submit once you have ensured everything is correct.

Once the input is configured, execute “index=<configured_index>” query to validate that the events are being received.

## Configure Event Types on Splunk Search Head Instance
To use the CIM mapped fields, user first needs to configure the event type to provide the index in which the data is being collected. To configure event type:
* Navigate to Settings > Event types.
* Select “Sophos XG Firewall Add-on For Splunk” from the App dropdown.
* Click on sophosxg_idx.
* Update “index=main” with “index=<your_configured_index>” in the existing definition to use your configured index.
* Click Save.


# OPEN SOURCE COMPONENTS AND LICENSES
* None


# TROUBLESHOOTING
* To check the fields extracted by the TA, execute query "index=<your_index_name>" in Splunk in verbose mode.

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/TA-sophos_xg_firewall/
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# SUPPORT
* Support Offered: No


### Copyright (C) 1997-2021 Sophos Ltd. All Rights Reserved.