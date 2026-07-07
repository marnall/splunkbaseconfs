# Dell PowerScale App for Splunk
## OVERVIEW

- The Dell PowerScale App for Splunk builds dashboards for Data Visualization that uses the data that gets indexed in Splunk via Dell PowerScale Add-on for Splunk.
- Author : Dell
- Version : 3.0.0
- Prerequisites:
    - Dell PowerScale Add-on for Splunk must be installed and inputs need to be configured to populate data on the dashboards.
- Compatible with:
    - Splunk Enterprise versions: 9.0.x, 8.2.x, 8.1.x
    - OS: Linux, Windows
    - Browser: Google Chrome, Mozilla Firefox

## RELEASE NOTES

### Version 3.0.0
  - Changed logo.
  - Added dashboard "Smart Quotas" to visualize User Quota data.

### Version 2.5.0
  - Changed branding of the app.

### Version 2.4.0
  - [Cluster Inventory] Node details panel in the Cluster Inventory dashboards shows wrong Up time.

## RECOMMENDED SYSTEM CONFIGURATION

- Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

  - This app has been distributed in two parts.
    1. Dell PowerScale Add-on for Splunk, which gathers data from Dell Isilon platform.
    2. Dell PowerScale App for Splunk, which uses data collected by Dell PowerScale Add-on for Splunk, runs searches on it and builds dashboard using indexed data.
  - This App can be set up in two ways:
    1. Standalone Mode:
        - Here both the apps reside on a single machine.
        - Install the Dell PowerScale App for Splunk and Dell PowerScale Add-on for Splunk on a single machine.
        - The Dell PowerScale App for Splunk uses the data collected by Dell PowerScale Add-on for Splunk and builds the dashboard on it.
    2. Distributed Environment: 
        - Install App and Add-on on search head,  Only Add-on on forwarder system and need to create index manually on Indexer. 
        - Here also both the apps resides on search head machine, but no need to configure Add-on on search head.
        - Only Add-on needs to be installed and configured on forwarder system.
        - On Indexer, Create index from menu Settings->Indexes->New. Give the name of index (for eg. isilon), which has been used in Add-on on forwarder system.
        - Execute the following command on forwarder to forward the collected data to the indexer.
       $SPLUNK_HOME/bin/splunk add forward-server <indexer_ip_address>:9997
        - On Indexer machine, enable event listening on port 9997 (recommended by Splunk).
        - Dell PowerScale App for Splunk on search head uses the received data and builds dashboards on it.

## INSTALLATION

Follow the below-listed steps to install an Add-on from the bundle:

- Download the App package.
- From the UI navigate to `Apps->Manage Apps`.
- In the top right corner select `Install app from file`.
- Select `Choose File` and select the App package.
- Select `Upload` and follow the prompts.

    OR

- Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## UPGRADE

Follow the below steps to upgrade the App.

- Go to Apps > Manage Apps and click on the "Install app from file". 
- Click on "Choose File" and select the Dell PowerScale App for Splunk installation file. 
- Check the Upgrade app checkbox and click on Upload.
- Restart the Splunk instance.

## TROUBLESHOOTING

If dashboards are not getting populated:

- If you are using the custom index, then make sure that `isilon_index` macro is updated accordingly.
- Make sure you have the data in selected time range.
- Make sure that the 'cluster_config' input is enabled. It can be checked by searching 'cluster_config' on 'Inputs' page of 'Dell PowerScale Add-on for Splunk'.
- The dashboards can take some time before the data is returned which will populate some of the panels. A good test to see that you are receiving all of the data we expect is to run this search after several minutes:
    - isilon_index | stats count by sourcetype

- In particular, you should see these sourcetypes:
    - emc:isilon:rest
    - emc:isilon:syslog
- For "emc:isilon:syslog": 
      - Check the syslog file in /etc/mcp/override/syslog.conf - it should have @<forwarders_ip_address> in front of the required log file and !* at the end of the syslog.conf file. Also run following command to see whether the syslog forwarding is enabled or not:
        1. For Dell Isilon cluster with oneFS version 8.x.x and later - isi audit settings view, isi audit settings global view

      - Dell Isilon forward syslog and audit logs on 514 udp port by default. Please make sure port 514 is open and available for Isilon syslogs.

- If you don't see these sourcetypes, check the input log files. User can see input related logs at $SPLUNK_HOME/var/log/splunk/ta_emc_isilon_isilon.log

- If "User" dropdown is not populating any values:
    - Verify you have configured the account in the Add-on.
    - If you are on distributed environment installation and configuration of Add-on is mandatory on Search Head.
    - If you are not seeing desired username:
        - Navigate to `Settings->Searches, Reports, and Alerts`. Select "TA_EMC-Isilon" in App dropdown and "nobody" in Owner dropdown, and run the "EMC-Isilon-Syslog-user-lookup-All-Time" search. Wait for few minutes until scheduled searches populates the dropdown.
        - Verify the account is configured for each hosts for which syslog data is getting collected.

- NOTE:
    - Values under "User" dropdown is not dependent on the selection of "Cluster" dropdown.
    - Under "FS Audit Logs" dashboard, the "Most Active Users" panel is not dependent on "User" dropdown.

## DISABLE APP

To disable the App, you must be logged in to Splunk as an Administrator and follow the steps below.
  - Go to 'Manage Apps' from Splunk's home page.
  - In the search box, type the name of the app, and then click Search. In the Status column, next to App, click Disable.

## UNINSTALL ADD-ON
- Uninstalling from a Standalone Environment
    - Disable the App from the Splunk user interface as detailed above.
    - Log in to the Splunk machine from the backend and delete the App folders. The app and its directory are typically located in $SPLUNK_HOME/etc/apps/<appname>.
    - Verify that no local configuration files related to Dell PowerScale App for Splunk are available in the $SPLUNK_HOME/etc/system and $SPLUNK_HOME/etc/users folders. If the local folder is present, remove it as well.
    - Restart Splunk

- Uninstalling from a distributed or clustered environment
    - In a cluster or distributed environment, the Dell PowerScale App for Splunk is installed on all the Search Heads and the Dell PowerScale Add-on for Splunk is installed on Search Heads and Forwarders.
    - The steps to uninstall the App and Add-on are the same as for Standalone.
    - To perform any installation or uninstallation step on all the search nodes of a distributed environment, use a deployer manager.
    - From the deployer machine, go to $SPLUNK_HOME/etc/cluster/apps and remove the App and Add-on folders and execute the luster bundle command. [Refer](https://docs.splunk.com/Documentation/Splunk/latest/DistSearch/PropagateSHCconfigurationchanges)

## SAVEDSEARCHES

This application contains following six saved searches, which are used in the dashboard. 

- EMC-Isilon-Cluster-Stats-lookup
    - This saved search is used to populate "ClusterStatsLookup" lookup

- EMC-Isilon-Cluster-lookup
    - This saved search is used to populate "ClusterNameLookup" lookup

- EMC-Isilon-Disk-lookup
    - This saved search is used to populate "NodeDiskLookup" lookup

- EMC-Isilon-NodeMapping-lookup
    - This saved search is used to populate "NodeMappingLookup" lookup

- EMC-Isilon-Users-Sid-lookup
    - This saved search is used to populate "UsersSidLookup" lookup

- EMC-Isilon-Cluster-Summary
    - This saved search is used to get summary details of cluster

## SUPPORT

- Access questions and answers specific to Dell PowerScale App For Splunk at https://answers.splunk.com.
- Support Offered: Yes
- Support Email: support@crestdatasys.com
- Please visit https://answers.splunk.com, and ask your question regarding Dell PowerScale App For Splunk. Please tag your question with the correct App Tag, and your question will be attended.

### Copyright (C) 2023 Dell Technologies Inc. All Rights Reserved.
