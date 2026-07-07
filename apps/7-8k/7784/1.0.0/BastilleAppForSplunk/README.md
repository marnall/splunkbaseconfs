# Bastille App For Splunk

## OVERVIEW
* Bastille senses, identifies and localizes radio threats, providing the ability to accurately quantify risk and mitigate threats to network infrastructure

## COMPATIBILITY MATRIX
* Splunk version: 9.3.x, 9.2.x, 9.1.x
* Python version: Python3
* OS Support: Independent
* Browser Support: Independent


## RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk Enterprise configuration of [Search Head, Indexer and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## RELEASE NOTES

### Version 1.0.0

* Added dashboards for Overview, Encryption details, Asset Management, Device Details, Tag Details, Sensor Details, and Transmission Data Details
* Added saved search to trigger alert based on bastille tag configured in macro

## INSTALLATION
Bastille App For Splunk can be installed through UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `Bastille App For Splunk` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This App can be set up in two ways:

1. Standalone Mode
    * Install the Bastille App For Splunk.
    * Follow all the steps mentioned in `Data Collection` section to configure the App.
2. Distributed Environment
    * Install the Bastille App For Splunk on the Search Head and Heavy Forwarder.
    * Follow the steps all steps from  `Data Collection` section on Heavy Forwarder and search head.
    * In case of Search Head Clustering, make sure that steps from `Data Collection `are configured on Heavy Forwarder.
    * Follow the steps from `Data Collection` section on Search Head. Following these steps will replicate the configuration on all search heads.
3. Cloud Environment1
    * Install the Bastille App For Splunk on Search Head.
    * Install the Bastille App For Splunk on IDM instance and configure it. (For the IDM instance Splunk support team will help) Or Setup the Bastille App For Splunk on the On-Premise Heavy Forwarder.




### Data Collection
To collect data in the Splunk index,

1. Create an HEC token and select the appropriate index and sourcetype. For reference: https://docs.splunk.com/Documentation/Splunk/9.3.0/Data/UsetheHTTPEventCollector
2. Using HEC: Use the same token and configure a Bastille instance to send the data to the Splunk environment.
    - Log into the Bastille Enterprise Admin Console.
    - In the Resources group, click Webhooks.
    - In the upper right corner, click Create.
    - Enter a Name for the webhook.
    - From the Type list, select Splunk.
    - From the Event list, select one or more of the event feeds to send from Bastille. 
    - Enterprise to Splunk.
    - Enter the Splunk URL.
        - This is the Splunk HTTP Event Collector URL. You may need to speak with your Splunk administrator to obtain this URL.
    - In the Request Parameters group, click Add.
    Enter the Splunk token Name and Value. 
    - The Splunk token value comes from your Splunk instance.
    - Select Include Events Check to send a test message for each event selected.
    - Click Test Connection to create a test event and POST it to Splunk.Bastille Enterprise reports success if all messages resolve. If one or more events experiences a problem, Bastille Enterprise reports a failure.
    - If the test succeeds, click Save.
3. After updating the token to the product Bastille data will be collected in the given Splunk Instance.
4. Sourcetype for the collected Bastille data would be bastille.




### Dashboards


1. Overview: This dashboard provides an overview of all Bastille dashboards.
    * Overview Dashboard Panel:
        1. Encryption Breakdown: This panel displays the Pie chart of all the encryption with respect to count.
            * DrillDown -> Clicking on any segment of the pie chart the Encryption Overview Dashboard will populate with relevant details.
        2. Top 10 Device Breakdown: This panel displays the Bar chart of the top 10 devices breakdown.
            * DrillDown -> Clicking on any column of panel Device Details Dashboard will populate with relevant details..
        3. User Breakdown: This panel displays the Pie chart of all the user with respect to count.
            * DrillDown -> Clicking on any segment of the pie chart the device details Dashboard will populate with relevant details.
        4. Device Model Classification : This panel displays the Pie chart of all the Device Model with respect to count.
             * DrillDown -> Clicking on any segment of the pie chart the device details Dashboard will populate with relevant details.
        5. Top 20 Networks: This panel displays the Bar chart of the top 20 Networks with relevant details.
            * DrillDown -> Clicking on any column of panel Encryption Overview Dashboard will populate.
        6. Top 20 Tags: This panel displays the Bar chart of the top 20 Tags with relevant details.

2. Encryption Details: This dashboard provides details on Encryption.
    *  Encryption Details Dashboard Panel:
        1. Top 20 Network Encryption Mapping:- This panel provides sankey diagram which connects Top 20 encryption type with network name.
        2. Network Encryption Details:- This panel provides overview of  Network Encryption.

3. Device Details: This dashboard provides details on the devices.
    * Device Details Dashboard Panel:
        1. Device Details:- This panel provides an overview of device related data.

4. Tag Details:
    * Tag Details Dashboard Panels: 
        1. Tag Details Dashboard: This panel provides an overview of tag related data.

5. Sensor Details
    * Sensor Details Dashboard Panels:
        1. Sensor Details: This panel provides an overview of sensor related data.
        2. Top 10 Highest Performing Sensors: This panel shows the top 10 sensor based on RSSI value.
        3. Top 10 Lowest Performing Sensors: This panel shows the top 10 sensor based on RSSI value.

6. Asset Management
    * Asset Management Dashboard Panels:
        1. Top 10 Manufacturer Distribution: This panel provides an top manufacturers .
        2. Asset Details: This panel provides an overview of all the asset related data
            * DrillDown -> Clicking on any row of This panel will redirect the user to that particular event in the search tab.

7. Transmission Data Details
    * Transmission Data Details Dashboard Panels:
        1. Top 10 Frame Type:- This panel displays the Pie chart of all the Frame Typex with respect to count.
        2. Top 10 Data Transfer By Devices:-  This panel displays the Bar chart of the top 10 Data Transfer By Devices.
        3. Data Transfer by Device Over Time:- This Panel shows line chart of Data Transfer by Device Over Time
        4. Top 10 Data Transfer by Transmitter ID:- This panel shows Top 10 Data Transfer by Transmitter ID
        5. Top 20 Data Volume Transfer Between Device and Transmitter ID: This panel provides sankey diagram which connects Data Volume Transfer Between Device and Transmitter ID.
        6. Top 20 Data Volume Transfer Between Device and User:- This panel provides sankey diagram which connects Data Volume Transfer Between Device and User.

8. Alert Details
    * Asset Details: This panel provides an information of the triggered alerts based on the configured `Bastille Tag Alert` savedserach.

## DATA MODEL
* The app includes one data model "Bastille". The acceleration for the data model is disabled by default. You can also enable the acceleration of the data model.
* Steps to enable/disable acceleration or change the acceleration period of data model:
    1. On Splunk's menu bar, Click on Settings -> Data models.
    2. From the list for Data models, Search for "Bastille" data model, click "Edit" in the "Action" column of the row for the Data model for which acceleration needs to be enabled or disabled.
    3. From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
    4. Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    5. If acceleration is enabled, select the summary range to specify the acceleration period.
    6. To save acceleration changes click on the Save button.
* Warning: The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer.

## MACROS
* **bastille_index:**
    * This macro is used in all the Bastille dashboards that are populated on indexed data. Default value is  index IN ("bn-data-observations-*"). 
    * User can update the macro by following this steps:
        * On Splunk's menu bar, Click on Settings ->"Advanced search" -> "Search Macros".
        * Search "bastille_index" macro
        * Click on the "bastille_index" macro and mention the index name in the Definition where data is incoming. Please see the sample below.
            * index IN ("bn-data-observations-*")
        *   Click on the Save Button.

* **bastille_summariesonly:**
    * This macro is used in all the Bastille dashboards that are populated on indexed data. Default value is summariesonly=false. 
    * User can update the macro by following this steps:
        * On Splunk's menu bar, Click on Settings ->"Advanced search" -> "Search Macros".
        * Search "summariesonly" macro
        * Click on the "summariesonly" macro and update the the Definition of summariesonly that you want. Please see the sample below.
            * summariesonly=true
        *   Click on the Save Button.

* **bastille_sourcetype:**
    * This macro is used in all the Bastille dashboards that are populated on sourcetype data. The default value is “sourcetype IN ("_json", "bastille")”. 
    * User can update the macro by following this steps:
        * On Splunk's menu bar, Click on Settings ->"Advanced search" -> "Search Macros".
        * Search "bastille_sourcetype" macro
        * Click on the "bastille_sourcetype" macro and update it. Please see the sample below.
            * sourcetype IN ("json")
            * sourcetype IN ("_json", "bastille")
        *   Click on the Save Button.

* **bastille_restricted_tags:**
    * This macro is used for alerting in case there's a restricted tag. The default value is “Bastille.tags IN ("Unauthorized")”. 
    * User can update the macro by following this steps:
        * On Splunk's menu bar, Click on Settings ->"Advanced search" -> "Search Macros".
        * Search "bastille_restricted_tags" macro
        * Click on the “bastille_restricted_tags” macro and update it. Please see the sample below.
            * Bastille.tags IN ("Unauthorized")
            * Bastille.tags IN ("Unauthorized", "Restricted")
        *   Click on the Save Button.

* **bastille_portal:**
    * This macro is used for providing DVR platform link. The default value is "dvr.vadc.bastille.cloud". 
    * User can update the macro by following this steps:
        * On Splunk's menu bar, Click on Settings ->"Advanced search" -> "Search Macros".
        * Search "bastille_portal" macro
        * Click on the "bastille_portal" macro and update it. Please see the sample below.
            * dvr.vadc.bastille.cloud
            * dvr_dummy.vadc.bastille.cloud
        *   Click on the Save Button.

## SAVEDSEARCHES
This application contains the following saved searches:

* `Bastille Tag Alert` - To trigger the alert for the specific mentioned tag in the `bastille_restricted_tags` macro.

    * For instructions on how to perform actions for triggering alerts, refer to this document: https://docs.splunk.com/Documentation/Splunk/latest/Alert/Setupalertactions

    * By default, this saved search will be enabled.

* `Bastille Delete Old Alerts` - To delete the lookup `bastille_tag_alert.csv` data that is older than 15 days.

    * By default, this saved search will be enabled.

* **NOTE**: If User want to enable/disable Savedsearches
    1. Click on setting > Searches, reports, and alerts
    2. Then select App as ˜Bastille App For Splunk and type the name in the filter section And User will see that savedsearch.
    3. click on the Edit button, it will display the enable/disable button.

## LOOKUPS
* `bastille_tag_alert`: This lookup contains details of triggered alerts. This lookup will be created and updated automatically.
* `akms_types`: This lookup contains mapping details for AKMS Types.
* `concentrator_id`: This lookup contains mapping details for Concentrator IDs.
* `map_id`: This lookup contains mapping details for Map IDs.

## TROUBLESHOOTING
### General Checks
* App icons are not showing up: The App does not require restart after the installation in order for all functionalities to work. However, the icons will be visible after one Splunk restart post installation.


### Data Collection
* Ensure that the HEC token is properly configured in Splunk. Go to Settings > Data Inputs > HTTP Event Collector and verify that the token is active and configured correctly.
* Ensure the token has the appropriate permissions for the index and source type you are using.
* Verify that the HEC endpoint is correctly configured and accessible. The endpoint URL should look something like https://splunk-server:8088.


### Dashboards
* Panel not populating:

* If your dashboard is not populating, then ensure the index in the macro matches the data present in the index. (To open macro go to setting->Advanced search->Search Macros).
* Check the percentage of acceleration in the data model. If the percentage is not 100%, not all data will load.  (To open data model go to setting->Data Models->Bastille)

## BINARY FILE DECLARATION

* md.cpython-39-x86_64-linux-gnu.so - This binary file is provided along with Charset-Normalizer module and source code for the same can be found at https://pypi.org/project/charset-normalizer/

## SUPPORT
* Support Offered: Yes
* Email: support@bastille.net

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/BastilleAppForSplunk
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

#### © 2019 - 2024 Bastille Networks Internet Security. All Rights Reserved. All Other Trademarks And Logos Are The Property Of Their Respective Owners.