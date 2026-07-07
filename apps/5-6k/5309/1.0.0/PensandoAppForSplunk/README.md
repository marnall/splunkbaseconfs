Pensando App for Splunk
=======================

# OVERVIEW
The Pensando App for Splunk provides several visualizations to view the Pensando DSC logs.

* Author - Pensando
* Version - 1.0.0
* Build - 24
* Creates Index - False
* Prerequisites - This application is dependent on Pensando Add-on for Splunk (TA-Pensando)
* Compatible with:
    * Splunk Enterprise version: 7.3.x and 8.0.x
    * OS: Platform independent
    * Browser: Safari, Chrome and Firefox

# RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk configuration

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    
    1. Pensando Add-on for Splunk, which parses data collected from Pensando DSC platform.
    2. Pensando App for Splunk, which adds dashboards to visualize this data.

* This app can be set up in two ways:
    
    1. **Standalone Mode**:
        * Install the Pensando App for Splunk and Pensando Add-on for Splunk.
        * The Pensando App for Splunk uses the data parsed by Pensando Add-on for Splunk and builds dashboards on it.
    2. **Distributed Environment**:
        * Install the Pensando App for Splunk and Pensando Add-on for Splunk on the search head.
        * User needs to manually create an index on the indexer (No need to install Pensando App for Splunk or Pensando Add-on for Splunk on indexer).

# INSTALLATION
Pensando App for Splunk can be installed through UI using "Manage Apps" > "Install app from file" or by extracting tarball directly into $SPLUNK_HOME/etc/apps/ folder.

# CONFIGURATION

## Configure Index in Macro:
    
If the user has selected a default index (**Note**: *By default, Splunk considers only `main` index as default index*) while configuring inputs for Pensando DSC logs, then no need to perform this step. But if the user has given any other index, then perform the following steps:
    
1. Go to "Settings" > "Advanced search" > "Search macros".
2. Select "Pensando App for Splunk" in "App" context dropdown.
3. Click on `pensandoindex` macro from the shown table.
4. In the macro definition default value will be `index="main"`. Update the definition with the index you used for data collection. For example: `index="<your_index_name>"`.

# TROUBLESHOOTING
* If you do not see any results in search then check whether you have correctly configured index in the `pensandoindex` macro. Also you can verify if the data is there in the index by running the search query `index="<your_index_name>"`.

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/PensandoAppforSplunk
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# SUPPORT
* Support Offered: Yes
* Support Email: splunkapp@pensando.io

### Copyright (C) 2017-2020 Pensando Systems Inc. All Rights Reserved.
