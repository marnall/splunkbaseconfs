# SOC Prime Attack Detective App for Splunk

## Description
SOC Prime Attack Detective App for Splunk connects your on-prem Splunk instance to [Attack Detective](https://tdm.socprime.com/attack-detective/) on the SOC Prime Platform.

Attack Detective intelligently and automatically queries security logs in the customer's security platform to identify data sources and then scan them in real time to provide cyber defenders with a holistic view of the organization’s cybersecurity posture, which enables smart data orchestration and next-gen automated threat hunting. Scans use prioritized detection content from Threat Detection Marketplace and correlate results with MITRE ATT&CK®.

Explore the outcomes consolidated into the detected ATT&CK techniques along with the impacted assets, services, and accounts. Analyze potential threat actors and adversary tools in use.

Instantly visualize a heatmap with triggered ATT&CK tactics and techniques and time of access for particular threat actors to find out if they can be attributed to a relevant attack.

Validate the risks by running selected queries in your Splunk instance and 
mark the outcomes based on the displayed behavior to prioritize your detection procedures.



## Requirements

SIEM: Splunk v. 9.x or higher.  
Note: If you have an all-in-one Splunk environment, use this guide to install the app. If you have a distributed Splunk environment, please contact SOC Prime support for help with installation since it may be specific to your configuration.

## Installation

There are two ways of installing the app: via the Splunk app listing or manually with the add-on package. 

To install the app via the listing, follow these steps:

1. Open the Splunk Web Console.
2. Select the gear icon on the **Apps** tab.
3. Click the **Browse more apps** button.
4. Type "SOC Prime Attack Detective App for Splunk" in the search field to find the app and proceed to its installation in your environment.

To install the add-on manually, follow these steps:

1. Open the Splunk Web Console.
2. In the Splunk Web Console, select the **Apps** tab.
3. Click the **Install app from file** button.
4. Select the "SOC Prime Attack Detective App for Splunk" package and proceed to its installation in your environment.

After successful installation, the app should appear as **SOC Prime Attack Detective App for Splunk** in Splunk’s **Apps** menu.

## Configuration

After installation, create an index for the App and configure getting the searches from Attack Detective on the **Inputs** tab:

1. Select *SOC Prime Attack Detective App for Splunk* in the main *Apps* menu.  
2. Create an index for this app:    
    2.1 In your Splunk header menu, open **Settings** > **Indexes** (in the **Data** section).    
    2.2 Click the **New index** button.    
    2.3 Give the index a name like **socprime**.    
    2.4 Click **Save**.
    2.5 Configure data rotation for this newly created index according to your organization's policies.    
3. Select the *Inputs* tab.  
4. Click *Create New Input*.  
5. Fill in the parameters:
* Name: Provide a descriptive name for this data input
* Interval: Time interval of input in seconds. The default value is 30
* Index: a technical parameter that should not be changed. Please, keep the Default value
* Attack Detective API key: The API key generated when configuring the Data Plane integration on the SOC Prime Platform
* Parallel Jobs Count: The number of searches that can be run simultaneously. Please, set it according to the performance of your Splunk instance
* Splunk REST API host and port: May be necessary for remote execution. Format: ["<splunk_host>:<port>"]. Default: ["localhost:8089"]
* Splunk REST API username: May be necessary for remote execution
* Splunk REST API password: May be necessary for remote execution
* Splunk REST API token: May be necessary for remote execution    

### Before the First Data Audit or Scan
The index created during the configuration is filled by the results of a special search run each hour. This data is used by Attack Detective to speed up data audits and scans. If you're going to run data audits or scans that cover time periods before the app has been installed (like for the last 7 or 30 days), you need to run the Reports search manually at least for the same period, which will generate all audit data historically for each day of the period. To do this:    
1. In the App menu, go to Reports.    
2. Click **Open in Search** for **SOC Prime Attack Detective Data Audit EventCodes with Indexes - Filling the Trend**.    
3. Select the same or greater time period as will be used for your data audit or scan in the calendar picker next to the Run button.    
4. Run the search.    
5. The search can take a long time depending on the selected period. You can send the job to the background. To do this:
    5.1 Go to **Job** > **Send Job to Background** in the menu under the search query.    
    5.2 The **Send Job to Background** window appears. Optionally, you can set the **Email when complete** checkmark and enter your email to receive an email notification when the job is finished.    
    5.3 Click the **Send to Background** button.    
6. Wait until the search is finished. After that, the index `socprime` will be populated with trended historical data, so you can run a Data Audit or Scan for the same period.    

Note that the [map](https://docs.splunk.com/Documentation/Splunk/9.3.2/SearchReference/Map) and [collect](https://docs.splunk.com/Documentation/Splunk/9.3.2/SearchReference/Collect) commands are used during Data Audits, and Splunk potentially can recognize them as risky.

All configurations related to investigations are made in [Attack Detective](https://tdm.socprime.com/attack-detective/) on the SOC Prime Platform. Before installing the SOC Prime Attack Detective App for Splunk, make sure to configure your [on-prem Splunk Data Plane](https://tdm.socprime.com/platform-settings/data-planes/) on the SOC Prime Platform.

To learn more, see the [Attack Detective User Guide](https://help.socprime.com/en/articles/6834634-attack-detective) (to open the Guide, you need to be logged in to your SOC Prime Platform account).

## Changelog:

* 1.0.0 — Initial release of the SOC Prime Attack Detective App for Splunk  
* 1.0.1 - Implemented changes to comply with the updated Splunk Cloud Platform compatibility
* 1.0.2 - Fixed bugs
* 2.0.0 — Made multiple updates:    
    * Improved interaction with Splunk by optimizing and speeding up the process of running searches    
    * Added dashboards that show the status of running searches in real time
    * Improved the speed of Data Audit. The Data Audit was refactored from scratch and all necessary data is trending in the App to speed up the Data Audit by Attack Detective.   
    * Added the Splunk Rest API authentication token parameter to input settings as an authentication option    
    * Now, after installing the app, you need to create a Splunk index for it. Note that if you upgrade from v1.0.0, you need to create an index as well    
* 2.0.1 — Made multiple updates:
    * Improved interaction with Splunk by optimizing and speeding up the process of running searches
    * Implemented changes to comply with the updated Splunk Cloud Platform compatibility
* 2.0.2 — Made multiple updates:
    * Improved interaction with SOC Prime API
    * Implemented changes to comply with the updated Splunk Cloud Platform compatibility
* 2.0.3 — Made multiple updates:
    * Implemented changes to comply with the updated Splunk Cloud Platform compatibility# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-attack-detective-app-for-splunk/bin/ta_soc_prime_attack_detective_app_for_splunk/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-attack-detective-app-for-splunk/bin/ta_soc_prime_attack_detective_app_for_splunk/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-attack-detective-app-for-splunk/bin/ta_soc_prime_attack_detective_app_for_splunk/aob_py3/setuptools/cli-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-attack-detective-app-for-splunk/bin/ta_soc_prime_attack_detective_app_for_splunk/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-attack-detective-app-for-splunk/bin/ta_soc_prime_attack_detective_app_for_splunk/aob_py3/setuptools/gui-arm64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-attack-detective-app-for-splunk/bin/ta_soc_prime_attack_detective_app_for_splunk/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-attack-detective-app-for-splunk/bin/ta_soc_prime_attack_detective_app_for_splunk/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-attack-detective-app-for-splunk/bin/ta_soc_prime_attack_detective_app_for_splunk/aob_py3/setuptools/gui.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-attack-detective-app-for-splunk/bin/ta_soc_prime_attack_detective_app_for_splunk/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-attack-detective-app-for-splunk/bin/ta_soc_prime_attack_detective_app_for_splunk/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-soc-prime-attack-detective-app-for-splunk/bin/ta_soc_prime_attack_detective_app_for_splunk/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
