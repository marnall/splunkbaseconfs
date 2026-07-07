# ABOUT THIS APP
The VulnDB Flashpoint App For Splunk is designed for visualization of collected vulnerabilities information using the VulnDB Flashpoint Add-on for Splunk. It mainly contains VulnDB Overview dashboards, Assets Dashboards, Remediation Dashboards, Inventory Dashboard, Configuration Dashboards and Bulk Upload Dashboard for the visualization of collected vulnerabilities.

* Author - Flashpoint
* Version - 2.6.1
* Creates Index - False
* Compatible with:
   * Splunk Enterprise version: 9.4.x, 9.3.x, 9.2.x and 9.1.x
   * OS: Platform independent
* This application is a VulnDB Flashpoint App For Splunk with visualization(VulnDBAppforSplunk).

# Requirements
* To visualize data, you need to configure Add-on for data collection.

# Recommended System Configuration

- Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

# Topology And Setting Up Splunk Environment

This app can be set up in two ways:

- Standalone Mode:

    - Install the "VulnDB Flashpoint App for Splunk" and "VulnDB Flashpoint Add-on for Splunk".
    - The "VulnDB Flashpoint App for Splunk" uses the data collected by "VulnDB Flashpoint Add-on for Splunk" and builds the dashboard on it.

- Distributed Environment:

    - Install the "VulnDB Flashpoint App for Splunk" and "VulnDB Flashpoint Add-on for Splunk" on the search head. User should not create data input.
    - User needs to manually create an index on the indexer (No need to install "VulnDB Flashpoint App for Splunk" or "VulnDB Flashpoint Add-on for Splunk" on indexer).

# Upgradation

Follow the below steps to upgrade the App.

* Go to Apps > Manage Apps and click on the "Install app from file". 
* Click on "Choose File" and select the VulnDBAppforSplunk installation file. 
* Check the Upgrade app checkbox and click on Upload. 
* Restart the Splunk instance.

## From previous versions To v2.6.1
- Follow the Upgradation section.
- Bump the javascript in browser to load new javascript changes.
    - In browser update the URL like this: `<http/https>://<yoursplunk>/en-US/_bump`.
    - click on `Bump version` button.
    - Remove the `_bump` from the url and load the dashboard.
## From previous versions To v2.6.0
- Follow the Upgradation section.
- Bump the javascript in browser to load new javascript changes.
    - In browser update the URL like this: `<http/https>://<yoursplunk>/en-US/_bump`.
    - click on `Bump version` button.
    - Remove the `_bump` from the url and load the dashboard.
## From previous versions To v2.5.0
- Follow the Upgradation section.
- Bump the javascript in browser to load new javascript changes.
    - In browser update the URL like this: `<http/https>://<yoursplunk>/en-US/_bump`.
    - click on `Bump version` button.
    - Remove the `_bump` from the url and load the dashboard.
## From previous versions To v2.4.0
- Follow the Upgradation section.
- No additional steps required.
## From previous versions To v2.3.0
- Follow the Upgradation section.
- Due to newly introduced lookup fields and panel filters in this version, Some panels won't show any data or data will be invalid after upgrade because the newly introduced lookup fields won't have past data.
- To avoid this, run all saved searches of this App sequentially, in order of their `Next Scheduled Time` in the `All Time` range to fill up all lookups with past data.

# Installation
* Using Web Interface
    * Log into Splunk with an administrator account.
    * Click on the gear icon for Application Management.
    * Click on the "Install app from file button".
    * Click the "Choose File" button and browse to the location on your local machine where the VulnDBAppforSplunk.tgz or VulnDBAppforSplunk.spl file is located and select it.
    * Click the "Upload button".

* Using Shell
    * Log into the shell for your Splunk server
    * Change to the Splunk application folder: 
        * cd $SPLUNK_HOME/etc/apps
    * Copy VulnDBAppforSplunk.tgz or VulnDBAppforSplunk.spl file into apps folder
    * Extract the application from the archive file: 
        * tar xzf VulnDBAppforSplunk.spl or tar xzf VulnDBAppforSplunk.tgz
    * Restart Splunk
        * $SPLUNK_HOME/bin/splunk restart

# Configuration
If you are collecting data in different index, you need to change macro definition in order to populate dashboard. Please follow below steps to change macro definition:
* Create/Update macros.conf file in local folder($SPLUNK_HOME/etc/apps/VulnDBAppForSplunk/local)
* Change definition as below:
```
[vulndb_index]
definition = index=<indexname>
```
Splunk by default only matches 50000 values in join so we need to add higher value in limits.conf. User needs to set value based on the events they are matching. Below is the steps to add limits.conf

* Create limits.conf in local folder($SPLUNK_HOME/etc/apps/VulnDBAppForSplunk/local)
```
[join]
subsearch_maxout = 500000

[searchresults]
maxresultrows = 500000
```
* Restart Splunk

# Disclosure Date Filter
Filter data based on the disclosure date of the vulnerability. The filter is applied on the below-listed dashboard panels.

|Dashboard            |Panels                                           |
|---------------------|-------------------------------------------------|
|Assets->Overview     |1. Vulnerable Assets                             |
|                     |2. Avg # of Vulns Per Asset                      |
|                     |3. Most Common Vulnerabilities                   |
|                     |4. Vulnerabilities by Business Function          |
|Assets->Information  |1. Vulnerability Associated with Host            |
|Remediation->Overview|1. # Vulnerable Assets                           |
|                     |2. # Unique Vulnerabilities in Assets            |
|                     |3. Top Vulnerabilities                           |
|                     |4. Newly Disclosed Vulnerabilities               |
|                     |5. Vulnerability Severity Breakdown              |
|Remediation->Information|1. Vulnerability Associated with Host         |

# Troubleshooting

- If Dashboards are not getting populated:
    - Disable and Re-enable the input to recollect the data. Check the logs, it will be more verbose and will give the insights on data collection.
    - If you are using custom index, make sure that macros `vulndb_index` has been updated accordingly.
    - If you don't see data in the given time range, try expanding it.
    - To check whether data is collected or not, run "`vulndb_index` | stats count by sourcetype" query in the search.

- If Changes are not reflected on UI after Upgrading the App.
    - Bump the javascript of the browser.
        - In browser update the URL like this: `<http/https>://<yoursplunk>/en-US/_bump`.
        - click on `Bump version` button.
        - Remove the `_bump` from the url and load the input page.

# Uninstall & Cleanup Steps
* Remove $SPLUNK_HOME/etc/apps/VulnDBAppforSplunk
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# Support
* Support Offered: Yes
* Support Email : support@riskbasedsecurity.com
* Supported by Flashpoint team through Splunk Community on best effort

# EULA

<https://help.fp.tools/en/articles/6653242-end-user-license-agreement-eula>

## Third party software

The following third-party libraries are used by this app.

* Chart.js - MIT - https://www.chartjs.org/
* jQuery - MIT - https://jquery.com/
* Font Awesome - CC BY 4.0 License - https://fontawesome.com/

Release Notes
-------------------------------------------------------------------------------

|Date|Version|Changes|
|----|----|----
|2019-04-24|1.1.0|1. Updated App icons
|2020-01-27|2.0.0|1. Overview Dashboard changes: Added Panels Severity Break Down, Vulnerabilities by Severity over Time, Top 10 Vulnerability Classes
||| 2. New dashboard named VulnDB Scores Overview
||| 3. Added Splunk 8 support and made Python2 and Python3 compatible
|2021-02-08|2.2.0|1. Changed the logo of VulnDB App For Splunk
||| 2. New dashboards named Overview in Asset and Remediation menu, Inventory , Bulk Upload
|2021-04-28|2.3.0| 1. Added feature to only show Assets whose Product's version is matching with Vulnerable Product's version
||| 2. Added feature to only show latest Products or Assets info in various panels
||| 3. Moved the Data Source Configuration Dashboard under Configuration Dashboard collection
||| 4. Added new Search Configuration Dashboard under Configuration Dashboard collection
||| 5. Added savedsearch to collect snapshot of Assets to Vulnerability mapping data in summary index
||| 6. Improved the color mapping in charts
||| 7. Added Disclosure Date filter on various panels
|2021-09-01|2.4.0| 1. Bundled jQuery v3.5.0 in the app package. This version of jQuery has security fixes and will be used by the app independently.
|2022-10-12|2.5.0| 1. Bundled jQuery v3.6.0 in the one of the visualization js file in app package. This version of jQuery has security fixes and will be used by the app independently.
|2023-05-08|2.6.0| 1. Bundled jQuery v3.6.0 in the app package. This version of jQuery has security fixes and will be used by the app independently.
||| 2. Added panels for newly added scores(epss_plus_score, epss_score, social_risk_score, ransomware_likelihood)
||| 3. Added new panels "All Affected Versions per Product" and "Location Data" for visualizing "Affected Products" and "Location" data.
||| 4. Updated the App's label and logo.
|2025-02-04|2.6.1| 1. Updated Splunk SDK to v2.1.0.

## Copyright 2025 Flashpoint
