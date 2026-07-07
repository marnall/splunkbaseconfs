Sophos Dashboards For Splunk
=======================

# OVERVIEW
The Sophos Dashboards For Splunk provides several visualizations to view the Sophos logs.

* Author - Sophos
* Version - 1.0.2
* Build - 1
* Creates Index - False
* Prerequisites - This application is dependent on Sophos Central Add-on For Splunk (TA-sophos-central-addon-for-splunk) and Sophos XG Firewall Add-on For Splunk (TA-sophos_xg_firewall)
* Compatible with:
    * Splunk Enterprise version: 7.3.x, 8.0.x and 8.1.x
	* Sophos Central APIs: v1
    * OS: Platform independent
    * Browser: Safari, Chrome and Firefox

# RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk configuration

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    
    1. Sophos Central Add-on For Splunk and Sophos XG Firewall Add-on For Splunk, which parses data collected from Sophos Central and XG Firewall respectively.
    2. Sophos Dashboards For Splunk, which adds dashboards to visualize this data.

* This app can be set up in two ways:
    
    1. **Standalone Mode**:
        * Install the Sophos Dashboards For Splunk, Sophos Central Add-on For Splunk and Sophos XG Firewall Add-on For Splunk.
        * The Sophos Dashboards For Splunk uses the data parsed by Sophos Central Add-on For Splunk and builds dashboards on it.
    2. **Distributed Environment**:
        * Install the Sophos Dashboards For Splunk, Sophos Central Add-on For Splunk and Sophos XG Firewall Add-on For Splunk on the search head.
        * Install the Sophos Central Add-on For Splunk and Sophos XG Firewall Add-on For Splunk on the indexer, if you are using Universal Forwader. User needs to manually create an index on the indexer (No need to install Sophos Dashboards For Splunk on indexer).

# INSTALLATION
Sophos Dashboards For Splunk can be installed through UI using "Manage Apps" > "Install app from file" or by extracting tarball directly into $SPLUNK_HOME/etc/apps/ folder.

# CONFIGURATION

## Configure Index in Macro:
    
If the user has selected a default index (**Note**: *By default, Splunk considers only `main` index as default index*) while configuring inputs for Sophos Central logs, then no need to perform this step. But if the user has given any other index, then perform the following steps:
    
1. Go to "Settings" > "Advanced search" > "Search macros".
2. Select "Sophos Dashboards For Splunk" in "App" context dropdown.
3. Click on `sophos_central_idx` macro from the shown table.
4. In the macro definition default value will be `index="main"`. Update the definition with the index you used for data collection. For example: `index="<your_index_name>"`.
5. Perform steps 4 and 5 for `sophosxgindex` macro as well.

# TROUBLESHOOTING
* If you do not see any results in search then check whether you have correctly configured index in the `sophos_central_idx` and `sophosxgindex` macro. Also you can verify if the data is there in the index by executing `index="<your_index_name>"` query.

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/SophosDashboardsForSplunk
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# SUPPORT
* Support Offered: No


### Copyright (C) 1997-2021 Sophos Ltd. All Rights Reserved.
