# About The App
The AIOps Incident Management App can be used to publish alerts/events from Splunk to AIOps Incident Management Cloud or AIOps Incident Management On-Prem/Hosted as stream of search results or individually in real-time.

Splunk supported versions
9.0, 8.2, 8.1, 8.0

Python supported versions
2.7 and 3.8

# Installation
    The AIOps Incident Management App is available on the Splunk Marketplace.

	If you do not want to install it from the marketplace, then proceed as follows:
		- Copy the App to any directory on the server, where Splunk is installed.
		- Navigate to the bin folder of Splunk e.g. <splunk_home>/bin
		- Enter the following command:
			./splunk install app <app path>/<appname.tar.gz>
			<app path> is the path where Splunk App is copied.
		- Restart Splunk:
		        ./splunk restart

	The AIOps Incident Management App is installed in the Splunk application. The App is displayed on the Splunk application homepage.
	Please refer to https://docs.moogsoft.com for more details.

# Distributed deployments

Use the following table to determine where and how to install this App in a distributed deployment of Splunk Enterprise or any deployment for which you are using forwarders to get your data in. Depending on your environment, your preferences, and the requirements of the App, you may need to install and configure the App in multiple places.

| Splunk platform instance type | Scheduled alerts* | Filtered events* |
| ----------------------------- | ----------------  | ---------------- |
| Forwarders                    | NO                | NO               |
| Indexers                      | NO                | YES              |
| Search Heads                  | YES               | YES              |

*Please view details in usage section for Scheduled alerts and Filtered events

# Configuration
For Default Configuration, URL, Severity, API Key, AIOps Incident Management Certificate PEM Path and select alert attributes to include in the event payload from setup page of the App.

NOTE: Provide the relative path from the bin directory of the App to the AIOps Incident Management Certificate(.pem) file.

If Proxy based configuration is enabled then Proxy Server HostName, Proxy Server Port, Proxy User and Proxy Password will be included in the event payload from setup page of App.

# Usage
## Scheduled alerts
A scheduled alert is an alert that runs on a regular interval, making it a type of scheduled search. You can add AIOps Incident Management Alert Integration from actions to a specific search or to all of them using `adddellaiopsimevent`. Also, you can remove AIOps Incident Management Alert Integration using `removedellaiopsimevent` from all saved searches. Following are the examples,
```
Settings -> Searches, reports, and alerts -> Existing/New alert -> Add AIOps Incident Management alert action
```
```
Search & Reporting -> Search "| rest /services/saved/searches | <Your Filter> | adddellaiopsimevent"
```
```
Search & Reporting -> Search "| rest /services/saved/searches | <Your Filter> | removedellaiopsimevent"
```

AIOps Incident Management Integration has provision to override the following parameters of the default configuration provided in the setup page.
* URL
* API Key
* Alert Severity
* AIOps Incident Management Certificate Path
* Proxy Server HostName
* Proxy Server Port
* Proxy User
* Proxy Password

## Filtered events (Additional configuration needed)
Search results streamed to the AIOps Incident Management Cloud or AIOps Incident Management On-Prem using custom streaming command named **dellaiopsimevent**. Following is the example.
```
Search & Reporting -> Search "index="LOG_INDEX" host="XYZ" severity="ERROR" | dellaiopsimevent"
```

# Support
This App is supported by Dell Inc.
https://www.moogsoft.com/support/