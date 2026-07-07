## BitSight App for Splunk

## OVERVIEW

* The BitSight App uses the data that are indexed in Splunk via an add-on for Data Visualization.
* For Data collection, please install the BitSight Add-on for Splunk available at https://splunkbase.splunk.com
* Author - BitSight Technologies, Inc.
* Version - 1.3.0

## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox
* OS: Platform Independent
* Splunk Enterprise version: 9.2.x, 9.1.x, 9.0.x
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

## RELEASE NOTES
### Version 1.3.0
* Updated dashboards to dedup data of finding Endpoint.

### Version 1.2.0
* Added new module for Benchmarked companies and updated dashboard accordingly.

### Version 1.1.0
* Added 'Remediation History' panel in 'My Company' dashboard.
* Added 'Benchmarking' dashboard.

### Version 1.0.0
* Added My Company and Work from Home - Remote Office dashboards.
* Added `BitSight - Get All Companies` saved search support.

## RECOMMENDED SYSTEM CONFIGURATION
* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This App can be set up in two ways:

1. Standalone Mode: Install the app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.
2. Distributed Environment: Install app on search head.

* App resides on search head machine to visualize the data coming from forwarders.

## INSTALLATION
Follow the below-listed steps to install an App from the bundle:

* Download the App package.
* From the UI navigate to `Apps-> Manage Apps`.
* In the top right corner select `Install the app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## UPGRADE

### General Upgrade Steps

* Go to Apps > Manage Apps and click on the "Install app from file".
* Click on "Choose File" and select the 'Bitsight App for Splunk' installation file.
* Check the Upgrade app checkbox and click on Upload.
* Restart the Splunk instance.

### From v1.2.0 to v1.3.0

* To upgrade BitSight App from v1.2.0 to v1.3.0 you need to follow general steps as mentioned above.

### From v1.1.0 to v1.2.0

* To upgrade BitSight App from v1.1.0 to v1.2.0 you need to follow general steps as mentioned above.

### From v1.0.0 to v1.1.0

* To upgrade BitSight App from v1.0.0 to v1.1.0 you need to follow general steps as mentioned above.

## CONFIGURATION
* The App does not require any specific configuration to make but in the case of the customized configuration of the BitSight Add-on for Splunk, the configuration of the App has to be changed.

## Configure Macros:
* If the user has selected a default index (**Note**: *By default, Splunk considers only the `main` index as default index*) in the "Data Input" configuration during BitSight Add-on for Splunk's configuration step, then no need to perform this step. But if the user has given any other index in the "Data Input" configuration, then perform the following steps:
    
1. Go to "Settings" > "Advanced search" > "Search macros".
2. Select "BitSight App for Splunk" in "App" context dropdown.
3. Click on the `bitsight_index` macro from the shown table.
4. In the macro definition default value will be `index IN (main)`. Update the definition with the index you used for data collection and save the configurations. For example: `index IN (<your_index_names>)`.


## DASHBOARD INFORMATION
* My Company: This dashboard contains different panels that will populate based on company selected from the Company Name dropdown.
* Work from Home - Remote Office: This dashboard help organizations to identify security risks in remote offices and networks.
* Benchmarking: This dashboard contains panels that compares the data among the different companies.

## SAVEDSEARCHES
* `BitSight - Get All Companies` saved search is used to get a list of companies from the data for the last 24 hours.
* `BitSight - Get All Companies - All Time` saved search is used to populate company_lookup lookup.
* `Bad Open Ports discovered` is used to discover Bad Open Ports in BitSight.
* `Compromised System- BitSight` is used to Compromised System in BitSight.
* `Patching Cadence` is used to get BitSight Confirmed vulnerabilities in Patching Cadence.
* `Vulnerabilities & Infections` is used to get Vulnerabilities & Infections in BitSight.

## LOOKUP
* `company_lookup`: This lookup contains a list of the companies for which the data is ingested.

## TROUBLESHOOTING
* If dashboards are not getting populated:
    * If dashboards are not getting populated then navigate to settings > Searches, Reports, and Alerts and run `BitSight - Get All Companies - All Time` saved search.
    * Make sure if you are using the custom index, then check that the `bitsight_index` macro needs to be updated.
    * Make sure you have data in a given time range.
    * To check whether data is collected or not, run the " \`bitsight_index\` | stats count by sourcetype" query in the search - you should see 2 sourcetypes:
        - bitsight
        - bitsight:benchmarking
    * Try expanding TimeRange.

## UNINSTALL APP
* To uninstall the App, the user can follow the below steps.
    * Remove $SPLUNK_HOME/etc/apps/BitSightAppforSplunk
    * To reflect the cleanup changes in UI, Restart Splunk Enterprise instance.

## SUPPORT
* Support Offered: Yes
* Support Email: splunk@bitsight.com

### (C) 2024 BitSight Technologies, Inc. and its Affiliates. All Rights Reserved.