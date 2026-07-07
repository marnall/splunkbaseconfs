# Splunk Technology App for GoogleSCC

## OVERVIEW

- The GoogleSCC App uses the data that are indexed in Splunk via add-on for Data Visualization. The GoogleSCC App for Splunk will provide the below dashboards:
    - Overview
    - Sources
    - Findings
    - Assets
    - Audit Logs
- Author - Google, Inc.
- Version - 2.0.2
- Prerequisites:
  - Google SCC Add-on must be installed and data-collection for sources, assets, findings and audit logs need to be configured to populate data on the dashboards.
  - Google SCC Service Account JSON or Credenitial Configuration(For AWS and Azure) and Organization Id for account configuration.
  - Google SCC Project Id and Subscription Id for data collection.
- Compatible with:
  - Splunk Enterprise version: 10.4.x, 10.2.x, 10.0.x, 9.4.x and 9.3.x
  - OS: Linux, Windows
  - Browser: Chrome, Firefox

## RECOMMENDED SYSTEM CONFIGURATION

- Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

  - This app has been distributed in two parts.
    1. GoogleSCC Add-on for Splunk, which collects data from GoogleSCC platform.
    2. The GoogleSCC App for Splunk for visualizing GoogleSCC data.
  - This app can be set up in two ways:
    1. Standalone Mode:
        - Install the GoogleSCC App for Splunk and GoogleSCC Add-on for Splunk.
        - The GoogleSCC App for Splunk uses the data collected by GoogleSCC Add-on for Splunk and builds the dashboard on it.
    2. Distributed Environment:
        - Install the GoogleSCC App for Splunk and GoogleSCC Add-on for Splunk on the search head. The user only needs to configure an account in GoogleSCC Add-on for Splunk but should not create data input.
        - If user wants to collect data into the index as well then Install only GoogleSCC Add-on for Splunk on the heavy forwarder with Enable index option in Inputs. User needs to configure an account, and create data input to start data collection. (Note: As GoogleSCC Add-on for Splunk collecting data directly to the KVStore so the user has to provide the credential information of Search head Splunk Instance on which user wants to forward the data)
        - User needs to manually create an index on the indexer (No need to install GoogleSCC App for Splunk or GoogleSCC Add-on for Splunk on indexer).

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

- Follow the below steps to upgrade the App.

    - Go to Apps > Manage Apps and click on the "Install app from file". 
    - Click on "Choose File" and select the Splunk Google SCC app installation file. 
    - Check the Upgrade app checkbox and click on Upload. 

## CONFIGURATION

- The App does not require any specific configuration to make but in case of customized configuration of the GoogleSCC Add-on for Splunk, the configuration of App has to be changed.

## DASHBOARD INFORMATION

  - Overview dashboard have following panels:
      - Findings by Finding Class : It shows findings based on the finding class in the pie chart.
      - Threats Over time : It shows the count of new findings with threats finding class detected over the selected time-range. It provides findings based on the severity in the bar chart.
      - Vulnerabilities Over time : It shows the count of new findings with vulnerabilities finding class detected over the selected time-range. It provides findings based on the severity in the bar chart.
      - Threats By Severity : It shows the total findings with threats finding class by severity in the form of a pie chart.
      - Vulnerabilities By Severity : It shows the total findings with vulnerabilities finding class by severity in the form of a pie chart.
      - Top 10 Categories by Threats : It shows a stacked bar chart of findings with threats finding class by severity for the top 10 categories.
      - Top 10 Categories by Vulnerabilities : It shows a stacked bar chart of findings with vulnerabilities finding class by severity for the top 10 categories.
      - Top 10 Asset Names by Threats : It shows a stacked bar chart of findings with threats finding class by severity for the top 10 Asset Name.
      - Top 10 Asset Names by Vulnerabilities : It shows a stacked bar chart of findings with vulnerabilities finding class by severity for the top 10 Asset Name.
      - Top 10 Projects by Threats : It shows a stacked bar chart of findings with threats finding class by severity for the top 10 Projects.
      - Top 10 Projects by Vulnerabilities : It shows a stacked bar chart of findings with vulnerabilities finding class by severity for the top 10 Projects.
      - Top 10 Asset Types by Assets : It shows the top 10 asset types based on assets count in the form of a Bar chart.
  - Sources dashboard have following panels :
      - 1000 Most Recent Sources : It shows one tabular panel having data of 1000 most recent unique sources collected. Table contains the following columns:
        - Organization ID
        - Source Name
        - Source Display Name
        - Source Description
  - Findings dashboard have following panels :
      - 1000 Most Recent Findings : It shows one tabular panel having data of 1000 most recent unique Findings collected. Table contains the following columns:
        - Organization ID
        - Finding Name
        - Category
        - Asset Name
        - Source Name
        - Security Marks
        - Finding Class
        - Severity
        - Project Name
        - Event Time
        - Update State
  - Assets dashboard have following panels :
      - 1000 Most Recent Assets : It shows one tabular panel having data of 1000 most recent unique assets collected. Table contains the following columns:
        - Organization ID
        - Asset Name
        - Asset Type
        - Resource Owners
        - Update Time
        - Redirect to SCC
  - Audit Logs dashboard have following panels :
      - Total Audit Logs : It shows the count of Audit Logs from all built-in services and integrated sources.
      - Audit Logs by Severity : It shows audit logs with different severity in the form of a pie chart.
      - Audit Logs by Resource Type : It shows audit logs with different resource types in the form of a pie chart.
      - 1000 Most Recent Audit Logs : It shows one tabular panel having data of 1000 recent audit logs collected and ingested into Splunk. Table contains the following columns:
        - Organization ID
        - Insert Id
        - Log Name
        - Resource Name
        - Resource Type
        - Method Name
        - Timestamp
        - Severity
        - Project Name

# Configure Macro #

- If you are collecting data in different index, you need to change macro definition in order to populate dashboard. Please follow below steps to change macro definition:
    - Create/Update macros.conf file in local folder
    - Change definition as below:
```
[googlescc_index]
definition = index=<indexname>
```


# User Action to update finding state #

 - This feature helps user to mark the finding state to either active/inactive. It can be used in the following way:
    - Go to the `Update Status` column provided on Findings Dashboard.
    - Click on `Mark as ACTIVE` or `Mark as INACTIVE` button to update the finding state to active or inactive respectively.

*Note : Updating finding state can only be performed by the Splunk user having admin roles.* 

## SAVED SEARCHES
This app contains the following saved searches.

 - googlescc_update_owner_lookup_from_index : Used to store the data of projectId and its corresponding role/owner value into the `googlescc_owner_lookup` lookup. It is executed every 6 minutes as the minimum time interval for data collection is 5 minutes.
 - googlescc_finding_state_loookup : Used to maintain finding state data in `updated_finding_state_lookup` lookup. It is running at an interval of 5 minutes which internally uses custom command `maintainfindingstatelookup` to maintain finding state lookup data and deletion of lookup data which has timestamp >30 minutes.


## CUSTOM COMMANDS
The following commands are included as a part of the app:

  - maintainfindingstatelookup
    - Purpose: To maintain finding state in `updated_finding_state_lookup` lookup and deletion of data in lookup which has timestamp >30 minutes.


## KNOWN LIMITATIONS
- Any data collected with TA v1.0.0 which is not at the organization level will not be visible on the dashboards.

## TROUBLESHOOTING

  - If dashboards are not getting populated:
    - If you are using the custom index, then make sure that “googlescc_index” macro is updated accordingly.
    - Make sure you have data in given time range.
    - To check whether data is collected or not, run " `googlescc_index` | stats count by sourcetype" query in the search.
    - Try expanding time range.
  - Finding state is not getting updated by clicking on the `Mark as ACTIVE/INACTIVE` button:
    - Check the log file related to user action generated under $SPLUNK_HOME/var/log/splunk/ta_googlescc_update_findings_status.log
    - Check the logs. They will be more verbose and will give the user insights on user action to update the finding state.
    - Try refreshing the panel.
    - If the state of the finding is not getting maintained after updating make sure that the KV Store is enabled on the Splunk.

## UNINSTALL APP

- To uninstall app, user can follow below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the GoogleSCCAppforSplunk folder from apps directory -> Restart Splunk

## COPYRIGHT INFORMATION

(C) 2026 Google

## SUPPORT

- Support Offered: Yes
- Support Hub: https://cloud.google.com/support-hub

## RELEASE NOTES

### Version 2.0.2
- Bumped the minimum required Python version to 3.13 as per Splunk standards.

### Version 2.0.1
- Updated Python SDK to v2.1.0.

### Version 2.0.0

  - Added 'Organization ID' filter in all dashboards.

### Version 1.0.0

  - Added following dashboards:
    - Overview
    - Sources
    - Findings
    - Assets
    - Audit Logs

## Binary file declaration

- google_auth - This binary file is provided along with google module and source code for the same can be found at https://pypi.org/
- googleapis_common_protos - This binary file is provided along with google module and source code for the same can be found at https://pypi.org/
- google_api_python_client - This binary file is provided along with google module and source code for the same can be found at https://pypi.org/
