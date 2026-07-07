Sophos Central Add-on For Splunk
=======================

# OVERVIEW
The Sophos Central Add-on For Splunk parses event logs collected from the Sophos legacy SIEM and endpoints, tenants and alerts data collected from Sophos Central. To visualize this data in Splunk dashboards, please install Sophos App For Splunk.

* Author - Sophos
* Version - 1.1.8
* Build - 1
* Creates Index - False
* Compatible with:
    * Splunk Enterprise version: 7.3.x, 8.0.x and 8.1.x
	* Splunk CIM version: 4.18.1
    * Sophos Central APIs: v1
    * OS: Platform independent
    * Browser: Safari, Chrome and Firefox

# RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk configuration

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    
    1. Sophos Central Add-on For Splunk, which parses event logs collected from the Sophos legacy SIEM and endpoints, tenants and alerts data collected from Sophos Central.
    2. Sophos App For Splunk, which adds dashboards to visualize the collected data.

* This app can be set up in two ways:
    
    1. **Standalone Mode**:
        * Install the Sophos App For Splunk and Sophos Central Add-on For Splunk.
        * The Sophos App For Splunk uses the data parsed by Sophos Central Add-on For Splunk and builds dashboards on it.
    2. **Distributed Environment**:
        * Install the Sophos App For Splunk and Sophos Central Add-on For Splunk on the search head. 
        * User needs to create data input on Splunk Universal/Heavy Forwarder to collect data from Sophos.
        * Install the Sophos Central Add-on For Splunk on the indexer, if you are using Universal Forwader. User needs to manually create an index on the indexer.

# INSTALLATION
Sophos Central Add-on For Splunk can be installed through UI using "Manage Apps" > "Install app from file" or by extracting tarball directly into $SPLUNK_HOME/etc/apps/ folder.

# CONFIGURATION

## Configure Inputs on Splunk Forwarder Instance
To configure inputs for Sophos Central Add-on:
* Login to Splunk WEB UI.
* Click on "Sophos Central Addon for Splunk" from left navigation panel.
* Click on the "Configuration" tab from the top navigation bar.
* Under "Add-on Settings" tab, configure Sophos Central client ID and client secret.
* If required, under "Proxy" tab, configure proxy settings and choose log level from "Logging" tab.
* Once configuration is done, click on the "Inputs" tab from the top navigation bar to configure input(s).
* Click on "Create New Input" button from top right and select one of "alert", "event", "tenant" or "endpoint" input for which the data collection needs to be initiated.
* Fill all the details for the selected input type in the pop up and click "Add" to save the input configuration.

Once the input is configured, execute “index=<configured_index>” query to validate that the data is being received.

## Configure Event Types on Splunk Search Head Instance
To use the CIM mapped fields, user first needs to configure the event type to provide the index in which the data is being collected. To configure event type:
* Navigate to Settings > Event types.
* Select “Sophos Central Add-on For Splunk” from the App dropdown.
* Click on sophos_central_idx.
* Update “index=main” with “index=<your_configured_index>” in the existing definition to use your configured index.
* Click Save.


# OPEN SOURCE COMPONENTS AND LICENSES
* None


# TROUBLESHOOTING
* To check the fields extracted by the TA, execute query "index=<your_index_name>" in Splunk in verbose mode.

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/TA-sophos-central-addon-for-splunk/
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# SUPPORT
* Support Offered: Sophos community support: https://community.sophos.com/sophos-integrations/f/splunk-apps-for-central-and-sophos-firewall


### Copyright (C) 1997-2021 Sophos Ltd. All Rights Reserved.