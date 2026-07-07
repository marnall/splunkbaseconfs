# About The Add-On
The TA-Splunk-Moogsoft Add-on is used to gather alerts/events from Splunk and publish it to Moogsoft Enterprise.

# TA-Splunk-Moogsoft version
2.0.0

# Splunk supported versions
8.0, 7.3, 7.2, 7.1, 7.0

# Python supported versions
2.7 and 3.7

# Installation
	The TA-Splunk-Moogsoft Add-on is available on the Splunk Marketplace. 
	
	If you do not want to install it from the marketplace, then proceed as follows:
		- Copy the Add-on to any directory on the server, where Splunk is installed.
		- Navigate to the bin folder of Splunk e.g. <splunk_home>/bin
		- Enter the following command:
			./splunk install app <app path>/<appname.tar.gz>
			<app path> is the path where Splunk Add-on is copied.
		- Restart Splunk:
		        ./splunk restart

	The TA-Splunk-Moogsoft Add-on is installed in the Splunk application. The Add-on is displayed on the Splunk application homepage.
	Please refer to https://docs.moogsoft.com for more details.

# Distributed deployments
Use the following table to determine where and how to install this Add-on in a distributed deployment of Splunk Enterprise or any deployment for which you are using forwarders to get your data in. You have to install and configure the Add-on in all systems as identified in the below table.

| Splunk platform instance type | Required |
| ----------------------------- | -------- |
| Forwarders                    | NO       |
| Indexers                      | NO       |
| Search Heads                  | YES      |

# Configuration
For Default Configuration, Configure Integration URL, Severity, Moogsoft Certificate PEM Path and select alert attributes to include in the event payload from setup page of the Add-on.

NOTE: Provide the relative path from the bin directory of the Add-on to the Moogsoft Certificate(.pem) file.

Selected Alert Attributes from setup page will be added to the payload with following mapping.

| Alert Attribute    | Mapping                    |
| ------------------ | -------------------------- |
| Alert Name         | configuration.name         |
| Alert Description  | configuration.description  |
| Alert Link         | configuration.alert_link   |
| Alert Trigger Time | configuration.trigger_time |
| Search Query       | configuration.search       |

# Usage
The TA-Splunk-Moogsoft Add-on has custom alert action named "Moogsoft Integration". User can create alert for the splunk search and select the Moogsoft Integration from actions.

Moogsoft Integration has provision to override the following parameters of the default configuration provided in the setup page.
 * Integration URL
 * Severity
 * Moogsoft Certificate Path (Required only for the On-Premises version of Moogsoft Enterprise and Splunk)

# Reference
See [Moogsoft Docs](https://docs.moogsoft.com/en/splunk-147411.html)

# Support
	This Add-On is supported by Moogsoft Inc.
	https://www.moogsoft.com/support/

