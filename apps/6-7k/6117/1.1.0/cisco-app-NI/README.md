# Cisco Nexus Dashboard Insights App for Splunk

## Overview

* The Cisco Nexus Insights for the data center stands out as the first comprehensive technology solution in the industry developed by Cisco for network operators to manage day-2 operations in their networks.
* Cisco Nexus Insights automates troubleshooting and helps rapid root-causing and early remediation. It also helps infrastructure owners comply with SLA requirements for their users.
* The Cisco Nexus Insights for the data center is supported on Cisco ACI and Cisco NX-OS/DCNM–based deployments.
* Cisco Nexus Dashboard Insights App for Splunk delivers centralized and real-time visibility of Anomalies & Advisories data collected by Cisco Nexus Dashboard Insights Add-On for Splunk.


* Author - Cisco Systems, Inc

* Version - 1.1.0


## Compatibility Matrix

|                                     |                                                           |
|-------------------------------------|-----------------------------------------------------------|
| Browser                             | Google Chrome, Mozilla Firefox, Safari                    |
| OS                                  | Linux, Windows                                            |
| Splunk Enterprise Version           | 9.3.x, 9.2.x, 9.1.x                                       |
| Supported Splunk Deployment         | Splunk Cloud, Splunk Standalone and Distributed Deployment|
| Nexus Insights version              | 6.3, 6.1                                           |
| Nexus Dashboard version             | 3.3, 2.1, 2.0                                                  |

## RELEASE NOTES
### Version: 1.1.0
* Updated app to make compatible with the Splunk Cloud.

## Recommended System Configuration

* Splunk search head system should have 16 GB of RAM and an octa-core CPU to run this app smoothly.


## Topology and Setting up Splunk Environment

     Install the main app (Cisco Nexus Dashboard Insights App for Splunk) and add-on app (Cisco Nexus Dashboard Insights Add-On for Splunk) on a single machine.

     * Here both the app resides on a single machine.
     * The main app uses the data collected by the Add-on app and builds dashboards on it.

     Install the main app and add-on app on a distributed clustered environment.
     * Install the App on a Search Head or Search Head Cluster.
     * Install and configure the Add-on on a Heavy forwarder or an Indexer. (Heavy forwarder recommended)


## Installation


Follow the below-listed steps to install an Add-On from the UI:


- Download the add-on package.

- From the UI navigate to  `Apps -> Manage Apps`.

- In the top right corner select `Install the app from file`.

- Select `Choose File` and select the App package.

- Select `Upload` and follow the prompts.

  OR

- Directly from the `Find More Apps` section provided in Splunk Home Dashboard.


## UPGRADE

### General upgrade steps:
* Navigate to `Apps -> Manage Apps` on Splunk menu bar.
* Click `Install app from file`.
* Click `Choose file` and select the App package.
* Check the `Upgrade` checkbox.
* Click on `Upload`.
* Restart Splunk.

### Upgrade to v1.1.0

* Follow the `General upgrade steps` section.
* No additional steps are required.


## Uninstallation and Cleanup

  This section provides the steps to uninstall App from a standalone Splunk platform installation.

  * (Optional) If you want to remove data from the Splunk database, you can use the below Splunk CLI clean command to remove indexed data from an app before deleting the app.
    * $SPLUNK_HOME/bin/splunk clean eventdata -index <index_name>

  * Delete the app and its directory. The app and its directory are typically located in the folder $SPLUNK_HOME/etc/apps/<appname> or run the following command in the CLI:
    * $SPLUNK_HOME/bin/splunk remove app [appname] -auth <splunk username>:<splunk password>

  * You may need to remove user-specific directories created for your app by deleting any files found here: $SPLUNK_HOME/bin/etc/users/*/<appname>

  * Restart the Splunk platform. You can navigate to Settings -> Server controls and click the restart button in Splunk web UI or use the following Splunk CLI command to restart Splunk:
    * $SPLUNK_HOME/bin/splunk restart

# Macros

* get_nexus_insights_index
    * If you are using a custom index in Add-on for data collection then kindly update the "get_nexus_insights_index" macro in the app.
* summariesonly
    * If you want to visualize only accelerated data then change this macro to summariesonly=true.
    * Default value of the macro is summariesonly=false.

# Alerts

* Email Alert for Advisory
    * This alert will be triggered if at any point severity is critical for advisories data in Nexus Insights Server.
    * By default, the alert will be disabled.

* Email Alert for Anomaly
    * This alert will be triggered if at any point severity is critical for anomalies data in Nexus Insights Server.
    * By default, the alert will be disabled.

# Alerts Configuration

* Enable Alert
    * Go to `Alerts` under `Notification` on the navigation bar.
    * Click on Edit for `Email Alert for Advisory` or `Email Alert for Anomaly`
    * In the dropdown click on `Enable`

* Email ID on which the mail is intended should be set in the App, to do that follow the steps
    * Go to `Alerts` under `Notification` on the navigation bar.
    * Click on Edit for `Email Alert for Advisory` or `Email Alert for Anomaly`
    * In the dropdown click on `Edit Alert`
    * Under the `Trigger Action` section write your Email ID in the `To` field
    * Click on Save

# DATA MODEL

* The app consists of one data model "Nexus Insights" and two datasets:
    * Advisories - Maps advisories details from the Nexus Insights Environment.
    * Anomalies - Maps anomalies details from the Nexus Insights Environment.
* The acceleration for the data model is disabled by default.
* As all the dashboards are populated using data model queries and real-time search doesn't work with the data model, all the real-time search filters are disabled.
* If you want to improve the performance of dashboards, you must need to enable the acceleration of datamodel. Please follow the below steps:
    * On Splunk menu bar, Click on Settings -> Data models
    * Filter with Cisco Nexus Dashboard Insights App for Splunk
    * In the "Actions" column, click on Edit and click Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
    * Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    * If acceleration is enabled, select the summary range to specify the acceleration period. The recommended acceleration period is 7 days. The acceleration period can be changed as per user convenience.
    * To save acceleration changes click on the Save button.
* Warning: The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer.

# REBUILDING DATA MODEL

* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:
    * On the Splunk menu bar, Click on Settings -> Data models.
    * Filter with Cisco Nexus Dashboard Insights App for Splunk
    * From the list for Data models, expand the row by clicking the ">" arrow in the first column of the row for the "Nexus Insights" Data model. This will display extra Data Model information in the "Acceleration" section.
    * From the "Acceleration" section click on the "Rebuild" link.
    * Monitor the status of "Rebuild" in the field "Status" of the "Acceleration" section. Reload the page to get the latest rebuild status.

## Troubleshooting

* If dashboards are not getting populated:
    * Check "get_nexus_insights_index" macro is updated if you are using the custom index.
    * Check either data model is accelerated or "summariesonly" macro is updated with summariesonly=true.
    * Make sure you have data in the given time range.
    * To check data is collected or not, run the "`get_nexus_insights_index` | stats count by sourcetype" query in the search. In particular, you should see these source types:
        * cisco:ni:anomalies
        * cisco:ni:advisories
    * Try expanding Time Range.

# Additional Features

In addition to out-of-the-box reporting and analytics capabilities for your Nexus Insights environment, the app includes a set of pre-defined dashboards for specific use cases:

* Anomalies: Graphical representation of anomalies that provides a segregated view of anomalies overall sites with all configured NI instances or segregated view of anomalies overall sites for any specific NI instance or information about a single site for NI instance.

* Advisories: Graphical representation of advisories that provides a segregated view of advisories overall sites with all configured NI instances or segregated view of advisories overall sites for any specific NI instance or information about a single site for NI instance.

* Workflow Action: The app provides a workflow action "Explore Anomaly Details on Nexus Insights Dashboard" for event type cisco_ni_anomalies to explore details about a specific anomalyID on Nexus Insights Instance.

## Support Information
Support Offered: Yes
Email: tac@cisco.com

## Copy Right Information

Copyright (c) 2023 Cisco Systems, Inc