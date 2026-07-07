# Splunk Technology App for SafeBreach
## OVERVIEW
* SafeBreach's mission is to change the way the industries deals with security and risk, and enable companies to use the security technologies in which they have invested in to their fullest.
* By validating those technologies against attacks, from the known to the latest emerging threats, they will drive risks, down on a continuous basis.
* They will be able to quantify risks to the business and drive a security strategy aligned with the company's business growth.
* SafeBreach Add-on for Splunk collects audit (using Syslog) and simulation (using API and Syslog) and Insights (using API) events and parses the fields. Data is mapped with the CIM datamodels for Enterprise Security Use cases.
* Author - SafeBreach, Inc.
* Version - 2.0.0
## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox, Safari
* OS: Linux, Windows
* Splunk Enterprise version: 8.1.X, 8.0.X, 7.3.X
* Supported Splunk Deployment: Splunk Cloud, Splunk Standalone and Distributed Deployment
## RECOMMENDED SYSTEM CONFIGURATION
* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.
## UPGRADE
### v1.0.0 to v2.0.0
* No additional steps are required.
## INSTALLATION
Follow the below-listed steps to install an App from the bundle:

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.
## CONFIGURATION
* The App does not require any specific configuration to make but in case of customized configuration of the SafeBreach Add-on for Splunk, the configuration of App has to be changed.
## DATA MODEL
* The app consist of one data model "SafeBreach". The acceleration for the data model is disabled by default. You can also enable the acceleration of the data model.
* Steps to enable/disable acceleration or change the acceleration period of data model:
    1. On Splunk's menu bar, Click on Settings -> Data models.
    2. From the list for Data models, Search for "SafeBreach" data model, click "Edit" in the "Action" column of the row for the Data model for which acceleration needs to be enabled or disabled.
    3. From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
    4. Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    5. If acceleration is enabled, select the summary range to specify the acceleration period.
    6. To save acceleration changes click on the Save button.
* Warning: The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the indexer.
## DASHBOARD INFORMATION
* Security Posture dashboard have following panels : 
    * Overall Result Breakdown : This panel visualizes details about the total count of each status. It is showing how many simulation_id's are having blocked, not_blocked, internal_fail, missed, stopped, prevented, detected, no-result and inconsistent status in a given time range.
    * Result Breakdown by Attack Phase : This panel visualizes details about the status over each attack_phase. It is showing per attack_phase, how many simulation_id's are having blocked, not_blocked, internal_fail, missed, stopped, prevented, detected, no-result and inconsistent status in a given time range.
    * Not-Blocked Results Over Time : This panel visualizes details about the not_blocked status over time range. It is showing timechart of how many simulation_id's are having not_blocked status in a given time range.
    * Result Breakdown by Target Simulator : This panel visualizes details about the status over each target simulator. It is showing per target simulator, how many simulation_id's are having blocked, not_blocked, internal_fail, missed, stopped, prevented, detected, no-result and inconsistent status in a given time range.
    * Result Breakdown by Security Control Category : This panel visualizes details about the status over each security control category. It is showing per security control category, how many simulation_id's are having  blocked, not_blocked, internal_fail, missed, stopped, prevented, detected, no-result and inconsistent status in a given time range.
    * Result Breakdown by MITRE Tactic : This panel visualizes details about the status over each MITRE Tactic. It is showing per MITRE Tactic, how many simulation_id's are having blocked, not_blocked, internal_fail, missed, stopped, prevented, detected, no-result and inconsistent status in a given time range.
    * Top 10 Threat Groups : This panel visualizes details about Top 10 threat groups over total count of status per threat group. It is showing how many simulation_id's are having blocked, not_blocked, internal_fail, missed, stopped, prevented, detected, no-result and inconsistent status from top 10 threat groups in a given time range.
    * Top 10 MITRE Techniques : This panel visualizes details about Top 10 MITRE Technique over total count of status per MITRE Technique. It is showing how many simulation_id's are having blocked, not_blocked, internal_fail, missed, stopped, prevented, detected, no-result and inconsistent status from top 10 MITRE Technique in a given time range.
    * Crown Jewels Posture : This panel visualizes details about the status over each data_asset. It is showing per data_asset, how many simulation_id's are having blocked, not_blocked, internal_fail, missed, stopped, prevented, detected, no-result and inconsistent status in a given time range.
    * Top 10 Attack Types : This panel visualizes details about Top 10 attack type over total count of status per attack type. It is showing how many simulation_id's are having blocked, not_blocked, internal_fail, missed, stopped, prevented, detected, no-result and inconsistent status from top 10 attack_type in a given time range.
    * Top 10 Protocols : This panel visualizes details about Top 10 protocols over total count of status per protocol. It is showing how many simulation_id's are having blocked, not_blocked, internal_fail, missed, stopped, prevented, detected, no-result and inconsistent status from top 10 protocol in a given time range.
    * Top 20 Attacks :  This panel visualizes details about Top 20 attack name,total count of status and individual count of each status.  It is how many simulation_id's are having blocked, not_blocked, internal_fail, missed, stopped, prevented, detected, no-result and inconsistent status in given time range per attack_name from top 20 attacks. 

* MITRE ATT&CK Heatmap dashboard have following panels : 
    * This dashboard contains table having different MITRE Techniques for corresponding MITRE Tactic with varied colour background based on the percentage. It is showing MITRE Technique name per MITRE Tactic and also showing how many simulation_id's are having blocked and not_blocked result per MITRE Technique and MITRE Tactic and showing percentage of how many simulation_id's are not blocked per MITRE Technique.
* SafeBreach Insights dashboard have following panels :
     * SafeBreach Insights (Daily Trends): This panel visualizes details about total numbers of active unique "ruleIds".
     * Standard IOCs (Daily Trends): This panel visualizes details about numbers of unique remediation data points of “non-behavioral” indicator types.
     * Behavioral IOCs (Daily Trends): This panel visualizes details about numbers of unique remediation data points of “behavioral” indicator.
     * Active Insights by Category: This panel visualizes details about numbers of active unique "ruleIds" by the field "category".
     * Active Indicators by Type: This panel visualizes details about numbers of active unique indicators.
     * SafeBreach Insights over Time by Category: This panel visualizes details about numbers of active unique "ruleIds" by the field "category" over specified time range.
     * Indicators Over Time by Type: This panel visualizes details about numbers of active unique indicators over the specified time range.
     * List of Insights: This panel visualizes details about Id, Name, Severity, Affected Targets, Impact and Explore (Link to notable event).
## TROUBLESHOOTING
* If dashboards are not getting populated:
    * Make sure if you are using the custom index, then check that “safebreach_index” macro needs to be updated.
    * Make sure you have data in given time range.
    * To check whether is data collected or not, run " `safebreach_index` | stats count by sourcetype" query in the search.
    * Try expanding TimeRange.

* If, `Not-Blocked Results Over Time` panel is showing incorrect event count in drilldown then verify that:
    * You must have to set time range more than one day in time range filter.
## UNINSTALL APP
To uninstall app, user can follow below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the `safebreach_app_for_splunk` folder from apps directory -> Restart Splunk.
## SUPPORT
* Email: <support@safebreach.com>
## COPYRIGHT INFORMATION
Copyright 2021 SafeBreach Inc. All rights reserved.
## RELEASE NOTES
### Version 2.3.2
* Added tracking id and alert name to the simulations results.
### Version 2.3.1
* Simulation results are now displayed only after all tests have completed event correlation from security controls.
### Version 2.1.4
* Updated safebreach support link in the setup page.
### Version 2.1.3
* Added a link to the Simulation Results in the Insights dashboard.
### Version 2.1.2
* Added Test End Time filter in Insight Dashboard
* Fixed Exclude No results bug in some widgets in security posture

### Version 2.1.1
* Add MITRE filter only relevant techniques per tactic
* Order the MITRE heatmap based on the ATT&CK
* Create base queries for the redundant queries to avoid processing time
* Remove the null/NA from the fields(any fields including deployments) from the dashboard
* Create Setup Page for SafeBreach app for splunk

### Version 2.1.0
* Additional filters Security Posture, MITRE ATT&CK and SafeBreach Insights dashboards.
* Added filters - Test Name, Deployment, Status, Result, Target.
* SafeBreach Insights now show insights per test.
* Additional fixes and improvements to different widgets and dashboards.

### Version 2.0.0
*  Updated Security posture dashboard to visualize Simulation API data. So now dashboard is visualizing both types of data i.e. syslog and api.
*  Added SafeBreach Insights dashboards to visualize Insights API data.
### Version 1.0.0
* Created following dashboards
    * Security Posture 
    * MITRE ATT&CK Heatmap
