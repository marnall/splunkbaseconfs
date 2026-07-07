CloudKnox App for Splunk
=======================

# OVERVIEW
The CloudKnox App for Splunk builds a dashboard from the data provided by CloudKnox Add-on for Splunk.

* Author - CloudKnox, Inc.
* Version - 1.3.0
* Build - 1
* Creates Index - False
* Prerequisites - This application is dependent on version 1.3.0 of CloudKnox Add-on for Splunk (TA-CloudKnox)
* Compatible with:
    * Splunk Enterprise version: 8.0.x ,8.1.x and 8.2.x
    * CloudKnox API v2 for audit,alert endpoints and v3 for PAR endpoint
    * OS: Platform independent
    * Browser: Safari, Chrome and Firefox

# Release Notes Version 1.3.0
* Bundled jQuery in app package and upgraded its version to v3.5.0
* Updated dashboard version to 1.1

# Release Notes Version 1.2.0
* Added API v3 support.
**Note**: Not backward compatible with TA <=v1.1.0.

# Release Notes Version 1.1.0
* Added support for CloudKnox platform audit logs
* Added support for CloudKnox alerts
* Added alert that triggers when a new super identity is indexed in Splunk

# Upgrade Steps
## Version 1.2.0. to Version 1.3.0
No special steps are required to upgrade the CloudKnox App for Splunk from version 1.0.0 to version 1.1.0.

## Version 1.1.0. to Version 1.2.0
No special steps are required to upgrade the CloudKnox App for Splunk from version 1.0.0 to version 1.1.0.

## Version 1.0.0. to Version 1.1.0
No special steps are required to upgrade the CloudKnox App for Splunk from version 1.0.0 to version 1.1.0.

# RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk configuration

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    
    1. CloudKnox Add-on for Splunk, which collects data from CloudKnox using REST API calls.
    2. CloudKnox App for Splunk, which adds dashboards to visualize the CloudKnox data

* This app can be set up in two ways:
    
    1. **Standalone Mode**:
        * Install the CloudKnox App for Splunk and CloudKnox Add-on for Splunk.
        * The CloudKnox App for Splunk uses the data collected by CloudKnox Add-on for Splunk and builds dashboards on it.
    2. **Distributed Environment**:
        * Install the CloudKnox App for Splunk and CloudKnox Add-on for Splunk on the search head. User does not need to configure an account or create an input in CloudKnox Add-on for Splunk on search head.
        * Install only CloudKnox Add-on for Splunk on the heavy forwarder. User needs to configure account and needs to create data input to collect data from CloudKnox.
        * User needs to manually create an index on the indexer (No need to install CloudKnox App for Splunk or CloudKnox Add-on for Splunk on indexer).

# INSTALLATION
CloudKnox App for Splunk can be installed through UI using "Manage Apps" > "Install app from file" or by extracting tarball directly into $SPLUNK_HOME/etc/apps/ folder.

# CONFIGURATION

## Configure Macros:
    
If the user has selected a default index (**Note**: *By default, Splunk considers only `main` index as default index*) in "Data Input" configuration during CloudKnox Add-on for Splunk's configuration step, then no need to perform this step. But if the user has given any other index in "Data Input" configuration, then perform the following steps:
    
1. Go to "Settings" > "Advanced search" > "Search macros".
2. Select "CloudKnox App for Splunk" in "App" context dropdown.
3. Click on `cloudknox(2)` macro from the shown table.
4. In the macro definition default value will be `index="main" sourcetype="cloudknox:$authSystemtype$:$category$"`. Update the definition with the index you used for data collection and save the configurations. For example: `index="<your_index_name>" sourcetype="cloudknox:$authSystemtype$:$category$"`.
5. Search `cloudknoxindex` macro and repeat the above step. The user is required to configure this macro in order to user the "cloudknox_super_identities_alert".
6. Next search `cloudknox_url_without_scheme` macro and replace "xyz.cloudknox.io" with the URL of your CloudKnox instance. The user is required to configure this macro in order to use the drill-down functionality in the "CloudKnox Alerts" dashboard.

## Configure Savedsearches:

This App contains below 2 schedule searches:
* cloudknox_super_identities_snapshot: This savedsearch updates cloudknox_si_snapshot KV store lookup to contain the latest super identities.
* cloudknox_super_identities_alert: This alert is generated when any new super identity is added.

Configuring savedsearches is only required if the user wishes to use "cloudknox_super_identities_alert" which triggers an alert when a new super identity is indexed in Splunk. Follow the below steps to configure the savedsearches:

1. Navigate to Settings > Searches, reports, and alerts
2. Find "cloudknox_super_identities_snapshot" search
3. Click on Edit > Edit Schedule
4. Enable the search and optionally update the "Schedule" and "Time Range" as per the requirement.
5. Thereafter find the "cloudknox_super_identities_alert" alert
6. Click on Edit > Edit Alert
7. Optionally modify the "Time Range" and "Cron Expression" as per the requirement
8. Add appropriate action to perform when the alert is triggered
9. Click "Save" to update the settings and enable the alert

# TROUBLESHOOTING
* If you do not see any results in search then check whether you have correctly configured index in the `cloudknox(2)` macro. Also you can verify if the data is there in the index by running the search query `index="<your_index_name>" source="cloudknox"`.

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/CloudKnoxAppforSplunk
* To reflect the cleanup changes in UI, restart Splunk instance. Refer https://docs.splunk.com/Documentation/Splunk/8.0.6/Admin/StartSplunk documentation to get information on how to restart Splunk.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

# OPEN SOURCE COMPONENTS AND LICENSES

* Some of the components included in CloudKnox App for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* jQuery
    * version: 3.5.0
    * URL: https://jquery.com
    * LICENSE: https://github.com/jquery/jquery/blob/main/LICENSE.txt

* Underscore JS
    * version: 1.6.0
    * URL: http://underscorejs.org
    * LICENSE: https://github.com/jashkenas/underscore/blob/master/LICENSE

# SUPPORT
* Support Offered: Yes
* Support Email: support@cloudknox.io

### Copyright (c) 2021 CloudKnox, Inc.
