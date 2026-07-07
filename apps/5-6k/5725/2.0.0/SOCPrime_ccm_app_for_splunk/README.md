# SOC Prime CCM App for Splunk


## Description
With SOC Prime CCM App for Splunk, you can continuously stream new rules and rule updates from the SOC Prime Platform to your cloud or on-prem Splunk instance.  


To enable rule streaming, configure Jobs in the Continuous Content Management (CCM) module of the SOC Prime Platform and specify them in the App's data input. Jobs are configured with Content Lists to select rules for deployment, Presets to automatically modify the rules' parameters, and Filters to include additional conditions. You can also set up and apply Custom Field Mapping profiles to make the names of indexes, fields, and even field values in the rule code match your custom data schema.  


This guide describes how to install the SOC Prime CCM App for Splunk and set up integration with CCM to enable the streaming of detection content directly into your Splunk environment.  


To obtain rules via the CCM module and stream them into your environment, you need access to the SOC Prime CCM API. For more details on the API, see our [Platform Guides](https://help.socprime.com/en/articles/6265791-api) (to open the Guides, you need to be logged in to your SOC Prime Platform account).


## Requirements


SIEM: Splunk v. 8.x or higher, or Splunk Cloud.  
Note: In distributed Splunk environments, this app should be installed in the search head.


## Installation


There are two ways of installing the app: via the Splunk app listing or manually with the add-on package.  


To install the app via the listing, follow these steps:


1. Open the Splunk Web Console.
2. Select the gear icon on the **Apps** tab.
3. Click the **Browse more apps** button.
4. Type "SOC Prime CCM App for Splunk" in the search field to find the app and proceed to its installation in your environment.


To install the add-on manually, follow these steps:


1. Open the Splunk Web Console.
2. In the Splunk Web Console, select the **Apps** tab.
3. Click the **Install app from file** button.
4. Select the "SOC Prime CCM App for Splunk" package and proceed to its installation in your environment.


After successful installation, the app should appear as **SOC Prime CCM App for Splunk** in Splunk’s **Apps** menu.


## Configuration


After installation, configure the rule import with the **Data Inputs** menu:


1. Select **Settings** > **Data Inputs**.
2. In the list of inputs, find **SOC Prime CCM App for Splunk** and click **Add new**.
3. Fill in all the required and optional parameters.


## Changelog:


* 1.0.0 — Initial release of the SOC Prime CCM App for Splunk providing functionality to import Alerts from the SOC Prime TDM Platform.  
* 1.0.1 — General minor improvements.  
* 1.0.3 — We've made several updates:  
    * Fixed filters in dashboards  
    * Resolved the issue with rule names that could lead to rule duplication  
    * Fixed and optimized the API script  
* 2.0.0 — We've introduced several substantial improvements:  
    * Streamlined the configuration of content to be deployed by introducing Jobs that replace all the separate settings used before. Now, you set up Jobs in SOC Prime Patform's CCM (adding Content Lists, Field Mappings, Presets, and Configs), and specify the Jobs in the App's data input.  
    * Removed deprecated options (Content List Name, Mapping Name, Preset Name, Alt Translation Config) from data input parameters.  
    * Added data input parameters to configure Jobs as well as rule exceptions, proxy, and distributed deployment.