# Splunk Technology App for Sonrai Security

## OVERVIEW
  * The Sonrai Security App uses the data that are indexed in Splunk via add-on for Data Visualization. The Sonrai Security App for Splunk will provide the below dashboards:
    * Ticket Trends
    * Risk Level
  * Author - Sonrai Security, Inc.
  * Version - 1.0.0

## Prerequisites:
* Sonrai Security Add-on must be installed and data-collection for tickets need to be configured to populate data on the dashboards.

## Compatibility Matrix
* Splunk version: 8.1.x and 8.2.x
* Python version: Python3
* OS Support: Linux (Centos) and Windows
* Browser Support: Chrome and Firefox

## RELEASE NOTES
### Version: 1.0.0
  * Added dashboards for the Tickets data.
    * Tickets Trends
    * Risk Level

## RECOMMENDED SYSTEM CONFIGURATION

* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

  * This app has been distributed in two parts.
    1. Sonrai Security Add-on for Splunk, which collects data from Sonrai platform.
    2. The Sonrai Security App for Splunk for visualizing Sonrai Tickets data.
  * This app can be set up in two ways:
    1. Standalone Mode:
        * Install the Sonrai Security App for Splunk and Sonrai Security Add-on for Splunk.
        * The Sonrai Security App for Splunk uses the data collected by Sonrai Security Add-on for Splunk and builds the dashboard on it.
    2. Distributed Environment:
        * Install the Sonrai Security App for Splunk and Sonrai Security Add-on for Splunk on the search head. The user only needs to configure an account in Sonrai Security Add-on for Splunk but should not create data input.
        * If user wants to collect data into the index as well then install only Sonrai Security Add-on for Splunk on the heavy forwarder with enable index option in inputs. User needs to configure an account, and create data input to start data collection.
        * User needs to manually create an index on the indexer (No need to install Sonrai Security App for Splunk or Sonrai Security Add-on for Splunk on indexer).

## INSTALLATION

Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## CONFIGURATION

* The App does not require any specific configuration to make but in case of customized configuration of the Sonrai Security Add-on for Splunk, the configuration of App has to be changed.

## DASHBOARD INFORMATION

  * Ticket Trends have following panels:
     * New Tickets
     * Snoozed Tickets
     * Risk Accepted Tickets
     * Ticket Trends by Status
     * CloudType Distribution
     * Top 10 Resource Types
     * Tickets
  * Risk Level have following panels:
     * Total Ticket by Severity
     * Ticket trends by Severity


## Configure Macros
* If the user has selected a default index in "Data Input" configuration during Sonrai Security Addon for Splunk's configuration step, then no need to perform this step. But if the user has given any other index in `Data Input` configuration, then perform the following steps:
    1. Go to "Settings" > "Advanced search" > "Search macros".
    2. Select "Sonrai Security App for Splunk" in "App" context dropdown.
    3. Click on `sonrai_index` macro from the shown table.
    4. Update the definition with the index you used for data collection and save the configurations. For example: `index="<your_index_name>"`.

> **NOTE**: *By default, Splunk considers only `main` index as default index*

## DATA MODEL
* The app consist of one data model "Sonrai". The acceleration for the data model is disabled by default. You can also enable the acceleration of the data model.
* Steps to enable/disable acceleration or change the acceleration period of data model:
    1. On Splunk's menu bar, Click on Settings -> Data models.
    2. From the list for Data models, Search for "Sonrai" data model, click "Edit" in the "Action" column of the row for the Data model for which acceleration needs to be enabled or disabled.
    3. From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
    4. Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    5. If acceleration is enabled, select the summary range to specify the acceleration period.
    6. To save acceleration changes click on the Save button.
* Warning: The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer.

## TROUBLESHOOTING

  * If dashboards are not getting populated:
    * Make sure if you are using the custom index, then check that `sonrai_index` macro needs to be updated.
      * How to configure macro:
        1. In Splunk Web, click Settings, then click Advanced search.
        2. Next to Search macros click Add new.
        3. Under Destination app make sure your app is selected.
        4. Under Name provide a name for your macro.
        5. Under Definition update the macro with the correct index.
    * Make sure that the constraint in the datamodel is not updated.
    * Make sure data is collected in given time range.
    * To check whether is data collected or not, run " `sonrai_index` | stats count by sourcetype" query in the search.
    * Try expanding TimeRange.
    * Make sure that `Sonrai` datamodel is enabled.
    * If large amount of data is collected in user instance, then update the `summariesonly` macro. Defination = `summariesonly=true`


## UNINSTALL APP

* To uninstall app, user can follow below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the SonraiAppForSplunk folder from apps directory -> Restart Splunk

## SUPPORT
* Email: support@sonraisecurity.com

## End User Licence Agreement:
https://eula.sonraisecurity.com/Sonrai%20Security%20Click-Through%20EUL%20Agreement.pdf

## COPYRIGHT INFORMATION

Copyright (C) Sonraí Security 2022.
