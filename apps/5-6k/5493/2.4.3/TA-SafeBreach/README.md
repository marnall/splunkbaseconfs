# Splunk Technology Add-on for SafeBreach

## OVERVIEW

* SafeBreach’s mission is to change the way the industries deal with security and risk and enable companies to use the security technologies in which they have invested to their fullest.
* By validating those technologies against attacks, from the known to the latest emerging threats, they will drive risks, down on a continuous basis.
* They will be able to quantify risks to the business and drive a security strategy aligned with the company's business growth.
* SafeBreach Add-on for Splunk collects audit (using Syslog) and simulation (using API and Syslog) events and parses the fields. Data is mapped with the CIM datamodels for Enterprise Security use cases.
* Prerequisites - SafeBreach API Token and Account ID for data collection
* Author - SafeBreach, Inc.
* Version - 2.2.8

## COMPATIBILITY MATRIX

* Browser: Google Chrome, Mozilla Firefox, Safari
* OS: Linux, Windows
* Splunk Enterprise version: 9.0.x, 9.1.x, 9.2.x
* Supported Splunk Deployment: Splunk Cloud, Splunk Standalone, and Distributed Deployment

## RECOMMENDED SYSTEM CONFIGURATION

* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.
* As the scale of data is too large, it is recommended to keep the start_date_time as latest as possible in insights input.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This Add-On can be set up in two ways:

1) Standalone Mode: Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy Forwarder for this setup.  
2) Distributed Environment: Install Add-on on Search Head and Heavy Forwarder (for REST API).

* Add-on resides on Search Head machine need not require any configuration here.
* Add-on needs to be installed and configured on the Heavy Forwarder system.
* Execute the following command on Heavy Forwarder to forward the collected data to the indexer.
  `/opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997`
* On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
* Add-on needs to be installed on Search Head for CIM mapping

## INSTALLATION

Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps-> Manage Apps`.
* In the top right corner select `Install the app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## UPGRADE

### From v2.0.0 to v2.0.1

* No additional steps are required.

### From v1.0.0 to v2.0.0

* No additional steps are required.

## CONFIGURATION

### For Syslog data collection

* Login into the SafeBreach portal with your credentials, and click on the `Administration` tab from the left side.
* Click on the `Integrations` tab, and then click on `Syslog CEF (outbound)`.
* Enter any name.
* Enter Syslog Server IP on which you want to collect the data.
* Enter UDP port.
* Select Event type from the dropdown of which you want to collect the data.
* Click on Add. The integration will be added. You can see that in the `Installed` tab.
* Now go to `Splunk Enterprise` and inside that go to `Settings -> Data inputs -> UDP`(For UDP input) or `Settings -> Data inputs -> TCP`(For TCP input).
* Click on `New Local UDP`/`New Local TCP`.
* Enter the port and make sure that you have written the same port as you have entered in the SafeBreach portal while configuration.
* Click on `Next`. Select Sourcetype from `Custom` Sourcetypes inside the dropdown i.e. safebreach:syslog.
* Select App Context and Index.
* Now click on `Review` and check your configuration.
* Now click on `Submit`.

### For API data collection

* From the Splunk Home Page, click on SafeBreach Add-on for Splunk and navigate to the Configuration section.
* In the Account tab, click on the `Add` button to configure a new Account.
* Enter the required details like Account Name (To uniquely identify accounts in Splunk), SafeBreach Host Name (URL), SafeBreach Account ID, SafeBreach API Token, and click on Save to save the configuration.
* If all the details are correct, an Account is created.
* To use a proxy as part of the connection to SafeBreach, go to the Proxy tab in the Configuration section and provide the required details. Don't forget to check the Enable option.
* To configure the Log Level, go to the Logging tab.
* Now go to the Input section for creating modular input.
* Click on the `Create New Input` button to configure a new Input.
  
#### SafeBreach Simulation Input

* Enter the required details like Name (To uniquely identify accounts in Splunk), SafeBreach Account (You have created in Account tab), Interval (Minimum and Default Value is 600s), Offset (Default Value of offset is 20m), Index, Start DateTime (In UTC format, eg.- 2021-03-20T05:40:58.000Z) and click on `Add` to save the configuration.
* If all the details are correct, Input is created.
* To manage the Modular Inputs, navigate to the Inputs section.
* If the user has successfully configured the SafeBreach Account, then Modular Inputs for the selected Account that have been created and should appear here.
* User can edit, delete, disable/enable and clone Modular Input by selecting specific Action.

* NOTE: On deleting input, the checkpoint of it won't be deleted, if input with the same name and same account is created again then it will start Data collection from the same checkpoint.

#### SafeBreach Insights Input

* Enter the required details like Name (To uniquely identify accounts in Splunk), SafeBreach Account (You have created in Account tab), Interval (Minimum and Default Value is 600s), Index, Start DateTime (In UTC format, eg.- 2021-03-20T05:40:58.000Z) and click on `Add` to save the configuration.
* If all the details are correct, Input is created.
* To manage the Modular Inputs, navigate to the Inputs section.
* If the user has successfully configured the SafeBreach Account, then Modular Inputs for the selected Account that have been created and should appear here.
* User can edit, delete, disable/enable and clone Modular Input by selecting specific Action.

* NOTE: On deleting input, the checkpoint of it won't be deleted, if input with the same name and same account is created again then it will start Data collection from the same checkpoint.

## Correlation SavedSearch
  
* The savedsearch is for creating notable events that will reflect the event if there is a change in ruleId and maxExecutionTime in the last 30 days.
* Note: If you want to add custom field on incident review, then visit the following link :
[Adding custom field on incident review page](https://www.splunk.com/en_us/blog/security/modifying-the-incident-review-page.html)

## TROUBLESHOOTING

### For Syslog

#### If sourcetype is not showing while configuring UDP Data input, then

* Check SafeBreach `Syslog CEF(outbound) Integration`. Make sure that you have entered correct Syslog Server IP and port.

#### If Data is not getting collected in Splunk

* Check log files inside `$SPLUNK_HOME/var/log/splunk/splunkd.log`.
* Check that you have selected correct sourcetype.

### For API

#### If Data is not getting collected in Splunk for API inputs

* Check log file inside `$SPLUNK_HOME/var/log/splunk/splunkd.log`.
* Make sure that you have entered correct Account ID and API Token while configuring Account.
* Check the Checkpoint value of your input and make sure that data is there during that Checkpoint value. For that check log file inside `$SPLUNK_HOME/var/log/splunk/ta_safebre(ach_simulation_input.log` (for simulation input) and `$SPLUNK_HOME/var/log/splunk/ta_safebreach_insights_input.log` (for insights input)

##### If events and fields are not displayed in Splunk (Insights Input)

* It is recommended to keep the start_date_time as latest as possible.

## UNINSTALL ADD-ON

To uninstall the add-on, the user can follow the below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the TA-SafeBreach folder from apps directory -> Restart Splunk.

## SUPPORT

* Email: <support@safebreach.com>

## COPYRIGHT INFORMATION

Copyright 2024 SafeBreach Inc. All rights reserved.

## RELEASE NOTES

### Version 2.4.3

* Bug fix for update the minimum polling interval in Audit input
* Reduce the minimum polling interval for Simulation input to 600 seconds.
* Reduce the minimum polling interval for Insights input to 600 seconds.

### Version 2.4.2

* Introduced configurable mapping for previously unparsed fields for Simulation Results.
* Reduce the minimum polling interval for Audit input to 60 seconds.

### Version 2.4.1

* Updated Splunk SDK for python
* Bug fixes
* Simulation results are now polled only after the correlation process has completed, ensuring more accurate and consistent data retrieval.

### Version 2.3.2

* Added mapping for tracking id and alert name.

### Version 2.2.9

* SSL verification always set to true for Cloud instances

### Version 2.2.8

* Fully compatible version with Python 3

### Version 2.2.7

* Parsed attack field for Remediation Data Type in Insight.

### Version 2.2.6

* Fixed issue of rendering the value for status field  with no-result values in Syslog Events.

### Version 2.2.5

* Fixed Syslog parsing to accommodate events in dashboard

### Version 2.2.4

* Stable verion for Addon builder 4.x and python 3 support
* Add MITRE filter only relevant techniques per tactic

### Version 2.2.3

* Sync _time for insights with test time
* Adjust Notables with the new data
* Add simulation result (result and result_code fields) details fields to Splunk add-on

### Version 2.2.2

* Updated the Addon app to addon builder 4.x
* Fix backward compatibility for password saved in previous versions

### Version 2.1.0

* CIM mappings added to the API based simulation events fetching.
* Parameters of simulations now stored in simulation events.
* Insights events now stored per test.
* Insights remediation data fields were normalized for easier processing.

### Version 2.0.1

* Fixed issue for data collection of Simulation & Insights data through SafeBreach API using proxy.

### Version 2.0.0

* Added support for data collection of Simulation & Insights data from SafeBreach API.
* Added correlation search to create notable events of Insights.

## Binary file declaration

The app does contain the binaries added by the Splunk Addon Builder.
