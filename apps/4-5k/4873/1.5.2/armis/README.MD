### Armis App For Splunk


#### OVERVIEW

- The Armis App uses the data that are indexed in Splunk via TA-Armis add-on for Data Visualization.
- The App uses data collected by the TA-Armis Add-on to present the below dashboards.
- The Armis App for Splunk will provide the below dashboards to visualize the Armis Data:
    - Alerts Overview(Syslog)
    - Alerts Overview(API)
    - Devices Overview
    - Vulnerabilities Overview
    - Affected Devices 
    (Note : "Affected Devices" Dashboard will not be displayed alongside with other Dashboards. It will get open on clicking "Affected Devices Count" value of "All Open Vulnerabilities" panel of "Vulnerabilities Overview" Dashboard)
 
- Author : Armis
- Version : 1.5.2

#### PREREQUISITES

- You should have `Technology Add-on for Armis` installed.

#### COMPATIBILITY MATRIX

- Browser: Google Chrome, Mozilla Firefox
- OS: Platform independent
- Splunk Enterprise version: 9.4.x, 9.3.x, 9.2.x, 9.1.x
- Supported Splunk Deployment: Splunk Cloud, Splunk Standalone, and Distributed Deployment

#### END USER LICENSE AGREEMENT
https://www.armis.com/legal/general-terms-and-conditions/

#### RELEASE NOTES

##### v1.5.2
  - Updated jQuery to support latest version
  - Checked compatibility with the latest Splunk version

##### v1.5.1
  - Added new fields "firstDetected" and "lastDetected" to KVStore lookup named "affected_devices_lookup" which contains affected devices ids against vulnerability id. 

##### v1.5.0
  - Added one saved search which stores the data of vuln-device mappings into kvstore lookup. 
  - Added "Vulnerability and Device Information" dashboard to see the vulnerabilities associated with device id. it gets opened on clicking of any cell of "Affected Devices Details" panel of "Affected Devices" Dashboard or "Last Seen Devices" panel of "Devices Overview" dashboard.
  - Minor dashboard enhancements.

##### v1.4.0
  - Added "Affected Devices" Dashboard that gets opened on clicking "Affected Devices Count" value of "All Open Vulnerabilities" panel of "Vulnerabilities Overview" Dashboard.
  - Renamed "Alerts Overview" Dashboard to "Alerts Overview(Syslog)". 
  - Added "Alerts Overview(API)" Dashboard for supporting alerts API data.
  - Added KVStore lookup named "affected_devices_lookup" that will contain affected devices ids against vulnerability id.

##### v1.3.1
  - Minor UI Changes in the Armis Vulnerabilities Dashboard.

##### v1.3.0
  - Added new dashboard for Armis Vulnerabilities Support which has meaningful panels and drilldowns for displaying Armis Vulnerabilities Data.

##### v1.2.0
  - Added Macros for index support. 

##### v1.1.0
  - Modified some of the queries for drilldown.

##### v1.0.1 - 05/01/2020
  * Initial Release

#### RECOMMENDED SYSTEM CONFIGURATION

- Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This app can be set up in two ways:

- Standalone Mode:
    - Install the "Armis App for Splunk" and "Technology Add-on for Armis".
    - The "Armis App for Splunk" uses the data collected by "Technology Add-on for Armis" and builds the dashboard on it.
- Distributed Environment:
    - Install the "Armis App for Splunk" and "Technology Add-on for Armis" on the search head. The user only needs to configure an account in "Technology Add-on for Armis" but should not create data input.
    - User needs to manually create an index on the indexer (No need to install "Armis App for Splunk" or "Technology Add-on for Armis" on indexer).

#### INSTALLATION

Follow the below-listed steps to install an App from the bundle:

- Download the App package.
- From the UI navigate to Apps-> Manage Apps.
- In the top right corner select Install the app from file.
- Select Choose File and select the App package.
- Select Upload and follow the prompts.

OR

- Directly from the `Find More Apps` section provided in Splunk Home Dashboard or go to the `Manage Apps` in the Splunk Dashboard then click on `Browse more apps`.

#### UPGRADE

Follow the below steps to upgrade the App.

* Go to Apps > Manage Apps and click on the "Install app from file". 
* Click on "Choose File" and select the Armis app installation file. 
* Check the Upgrade app checkbox and click on Upload.
* Bump the javascript in the browser to load new javascript changes.
    * In the browser update the URL like this : `<http/https>://<yoursplunk>/en-US/_bump`.
    * click on the `Bump version` button.


##### Upgrading from v1.4.0 to v1.5.0
- Follow the UPGRADE section.
- No additional steps are required.

##### Upgrading from v1.3.1 to v1.4.0
- Follow the UPGRADE section.
- No additional steps are required.

##### Upgrading from v1.3.0 to v1.3.1
- Follow the UPGRADE section.
- No additional steps are required.

##### Upgrading from v1.2.0 to v1.3.0
- Follow the UPGRADE section.
- No additional steps are required.

##### Upgrading from v1.1.0 to v1.2.0
- Follow the UPGRADE section.
- No additional steps are required.

##### Upgrading from v1.0.1 to v1.1.0
- Follow the UPGRADE section.
- No additional steps are required.

#### CONFIGURATION

- The App does not require any specific configuration to make but in case of customized configuration of the TA-Armis Add-on for Splunk, the configuration of App has to be changed.

#### DASHBOARD INFORMATION

**Alerts Overview(Syslog)** :-

- It has following panels:
    - Total Alerts - This panel displays single value count of total alerts generated.
    - Alerts by Severity - This panel displays pie chart of alerts categorized by severity.
    - Alerts by Title - This panel displays pie chart of alerts categorized by title of the alert.
    - Alerts over Time by Severity - This panel displays line chart which has severity field in it and categorized by the time alert is generated.
    - Alerts by Device Type - This panel displays bar chart of alerts categorized by the type of the device.
    - Alerts by Site - This panel displays bar chart of alerts categorized by the location of the device.
    - Recent Alerts - This panel will display table of the recent alerts which will show necessary fields included in the alerts data.
    (Note : This dashboard uses Syslog Alerts data)

**Alerts Overview(API)** :-

- It has following panels:
    - Total Alerts - This panel displays single value count of total alerts generated.
    - Alerts by Severity - This panel displays pie chart of alerts categorized by severity.
    - Alerts by Title - This panel displays pie chart of alerts categorized by title of the alert.
    - Alerts over Time by Severity - This panel displays line chart which has severity field in it and categorized by the time alert is generated.
    - Alerts by Device Type - This panel displays bar chart of alerts categorized by the type of the device.
    - Alerts by Site - This panel displays bar chart of alerts categorized by the location of the device.
    - Recent Alerts - This panel will display table of the recent alerts which will show necessary fields included in the alerts data.
    (Note : This dashboard uses API Alerts data)

**Devices Overview** :-

- It has following panels:
    - Total Devices - This panel displays single value count of total devices generated.
    - Devices by Risk Level - This panel displays pie chart of devices categorized by the level of risks.
    - Devices by Category - This panel displays bar chart of devices categorized by device category field.
    - Devices by Type - This panel displays bar chart of devices categorized by the types of devices.
    - Devices by Operating System - This panel displays pie chart of devices categorized by the operating system used by the device.
    - Devices by Site - This panel displays pie chart of devices categorized by the location of the device.
    - Last Seen Devices - This panel will display table of the recent devices which will show necessary fields included in the devices data. 

**Vulnerabilities Overview** :-

- It has following panels:
    - Total Open Vulnerabilities - This panel displays single value count of total open vulnerabilities generated.
    - Open Vulnerabilities By Severity - This panel displays pie chart of open vulnerabilities categorized by severity.
    - Open Vulnerabilities By Status - This panel displays pie chart of vulnerabilities categorized by the status.
    - Open Vulnerabilities Over Time - This panel displays line chart which will display open vulnerabilities generated over time.
    - Open Vulnerabilities Over Time By Severity - This panel displays line chart which will display open vulnerabilities generated over time and will be categorized by severity.
    - All Open Vulnerabilities - This panel will display table of all open vulnerabilities which will show necessary fields included in the vulnerabilities data and the table will be populated based on severity multiselect dropdown and CVSS Score text field.

**Affected Devices** :-

- This Dashboard gets populated and displayed on on clicking "Affected Devices Count" value of "All Open Vulnerabilities" panel of "Vulnerabilities Overview" Dashboard.
- It has following panels:
    - Associated Vulnerability ID - This panel displays the corresponding vulnerability id of the clicked "Affected Devices Count" value in "Vulnerabilities Overview" Dashboard.
    - Total Number of Affected Devices - This panel displays the exact count of the clicked "Affected Devices count" value.
    - All Affected Devices by Risk severity - This panel displays pie-chart of the "Affected Devices" by Risk severity.
    - Affected Devices Details - This panel displays table of the affected devices with the necessary fields that are present in the devices data. This panel gets updated based on the filters.

**Vulnerability and Device Information** :-

- This Dashboard gets populated and displayed on clicking any cell of "Affected Devices Details" panel of "Affected Devices" Dashboard or "Last Seen Devices" panel of "Devices Overview" dashboard.
- It has following panels:
    - Vulnerabilities associated with device id - This panel displays the associated vulnerabilities of the device id clicked on "Affected Device Details" panel of "Vulnerabilities Overview" Dashboard or "Last Seen Devices" panel of "Devices Overview" Dashboard.
    - Device Detail - This panel displays the device detail of the device id clicked on "Affected Device Details" panel of "Vulnerabilities Overview" Dashboard or "Last Seen Devices" panel of "Devices Overview" Dashboard.

#### CONFIGURE MACROS

- If the user has selected a default index (Note: By default, Splunk considers only the main index as default index) in the "Data Input" configuration during Technology Add-On for Armis configuration step, then no need to perform this step. But if the user has given any other index in the "Data Input" configuration, then perform the following steps:
- Go to "Settings" > "Advanced search" > "Search macros".
- Select "Armis App for Splunk (armis)" in "App" context dropdown.
- Click on the "get_armis_index" macro from the shown table.
- In the macro definition default value will be index IN (main). Update the definition with the index you used for data collection and save the configurations. For example: index IN (<your_index_names>).

#### SAVEDSEARCHES

- This Application contains the following Saved Searches.

| Saved Searches Name                                    | Description                                                                       | Interval |
| ------------------------------------------------------ | --------------------------------------------------------------------------------- | -------- |
| `update_affected_devices_lookup`       | Update vuln id and device ids in affected devices lookup from the armis:vuln:match sourcetype. | 24 hours  |

**NOTE**

* Enable and Run the savedsearch (on the search head in case of distributed environment) for the first time and then it will be scheduled to run daily @00:30 am.
* Run `update_affected_devices_lookup` after collecting all the vuln-device mappings data in the splunk (sourcetype=armis:vuln:match). Check `Successfully fetched all the vuln-match data from API` message in `ta_armis_vulnerability_<input_name>.log` file in logs.
* If you have collected vulnerabilities as well as vuln-device mappings data into custom index then update the `get_armis_index` macro and then run the savedsearch. 

#### TROUBLESHOOTING

- If Dashboards are not getting populated:
    - Disable and Re-enable the input to recollect the data. Check the logs, it will be more verbose and will give the insights on data collection.
    - If you are using custom index, make sure that macros `get_armis_index` has been updated accordingly.
    - If you don't see data in the given time range, try expanding it.
    - To check whether data is collected or not, run "get_armis_index | stats count by sourcetype" query in the search.

  **Note for "Affected Devices" and "Vulnerability and Device Information" Dashboard:** 
  
  - This Dashboard depends on "devices" and "vulnerabilities" data so to check whether the data for the same is collected 
     or not, run "get_armis_index | stats count by sourcetype" query in the search to check whether you have "armis:device"
     and "armis:cve" sourcetype present.
   - If you are using custom index for both "devices" and "vulnerability" input then make sure macros `get_armis_index` has been updated accordingly.
   - Also, make sure that you have data present in the lookup.
     You can run this query in search for checking the same :
     " | inputlookup "affected_devices_lookup" "

  **Note for "Alerts Overview(API)" Dashboard:**
  
   - This Dashboard depends on "devices" data so to check whether the data for the same is collected or not, run "get_armis_index | stats count by sourcetype" query in the search to check whether you have "armis:device" sourcetype present.

#### UNINSTALL APP
- To uninstall app, user can follow below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the armis folder from apps directory -> Restart Splunk.

#### CLEAN-UP APP

- To clean up app remove $SPLUNK_HOME>etc>users>your user name>armis>local folder.
- Restart Splunk.

#### SUPPORT
- Support Offered: Yes
- Email: support@armis.com

### Copyright (C) 2022 Armis Inc. All Rights Reserved.