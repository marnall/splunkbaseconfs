# RiskSense App For Splunk

## OVERVIEW

* The Apps deliver a user experience designed to make Splunk immediately useful and relevant for typical tasks and roles. The RiskSense App for Splunk will provide the below functionalities:
  * Dashboards to visualize the RiskSense data.
  * The App uses data collected by the RiskSense Add-on to present the above dashboards.

* Author - RiskSense
* Version - 1.1.0
* Build - 1
* Prerequisites - Risksense Add-on for Splunk
* Compatible with:
  * Splunk Enterprise version: 8.0.x, 7.3.x, 7.2.x and 7.1.x
  * OS: Platform independent

## END USER LICENSE AGREEMENT

https://risksense.com/customer-agreements/

## OPEN SOURCE COMPONENTS AND LICENSES

* Some of the components included in RiskSense App for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.

  * backports version 1.0 https://pypi.org/project/backports/ (LICENSE https://github.com/openSUSE/python-backports-generate/blob/master/LICENSE)

  * requests version 2.20.0 http://docs.python-requests.org/en/master/ (LICENSE https://github.com/requests/requests/blob/master/LICENSE)

  * certifi version 2019.11.28 https://pypi.python.org/pypi/certifi (LICENSE https://github.com/certifi/python-certifi/blob/master/LICENSE)

  * chardet version 3.0.4 https://pypi.python.org/pypi/chardet (LICENSE https://github.com/chardet/chardet/blob/master/LICENSE)

  * idna version 2.8 https://pypi.python.org/pypi/idna/2.8 (LICENSE https://github.com/kjd/idna/blob/master/LICENSE.rst)

  * urllib3 version 1.25.7 https://pypi.python.org/pypi/urllib3/1.25.7 (LICENSE https://github.com/shazow/urllib3/blob/master/LICENSE.txt)

  * PySocks version 1.7.1	 https://pypi.python.org/pypi/PySocks (LICENSE https://github.com/Anorov/PySocks/blob/master/LICENSE)

  * six version 1.13.0 https://github.com/benjaminp/six (LICENSE https://github.com/benjaminp/six/blob/master/LICENSE)

## RELEASE NOTES

* Version 1.1.0
  * Minor dashboard enhancements

## RECOMMENDED SYSTEM CONFIGURATION

* Splunk forwarder system should have 12 GB of RAM and a six-core CPU to run this Technology Add-on smoothly.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This Add-On can be set up in two ways:

1) Standalone Mode: Install the app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup
2) Distributed Environment: Install app on search head.

* App resides on search head machine to visualize the data coming from forwarders.

## INSTALLATION

Follow the below-listed steps to install an App from the bundle:

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

## UPGRADE

Follow the below steps when upgrading from RiskSense App for Splunk

* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Check the upgrade option.
* Select `Upload` and follow the prompts.
* Restart Splunk.

### SAVEDSEARCHES AND ALERTS

* RiskSense Hosts Critical Severity Alert - This alert triggers when the number of critical vulnerabilities will increase for a particular host.
* RiskSense Hosts High Severity Alert - This alert triggers when the number of high vulnerabilities will increase for a particular host.
* RiskSense Hosts Medium Severity Alert - This alert triggers when the number of medium vulnerabilities will increase for a particular host.
* RiskSense Hosts RS3 Alert - This alert triggers when RS3 increases or decreases for a particular host.
* RiskSense Applications Critical Severity Alert - This alert triggers when the number of critical vulnerabilities will increase for a particular application.
* RiskSense Applications High Severity Alert - This alert triggers when the number of high vulnerabilities will increase for a particular application.
* RiskSense Applications Medium Severity Alert - This alert triggers when the number of medium vulnerabilities will increase for a particular application.

### CONFIGURING EMAIL ALERT ACTION
  
* Follow below steps to configure email alert action for any of the savedsearch:
  * Navigate to `Settings -> Searches, Reports, and Alerts`.
  * Select App to be RiskSense App for Splunk.
  * In the Actions tab, click on `Edit -> Edit Alert`.
  * Go to `Trigger Actions -> Add Actions -> Send Email`.
  * Add details like To, Subject, Message and select appropriate attachments.
  * Click Save.

### LOOKUPS

* risksense_hosts_severity_details - This is a kvstore lookup which will consist of the severity details of all hosts.
* risksense_apps_severity_details - This is a kvstore lookup which will consist of the severity details of all applications.

## CUSTOM COMMAND

* `rsgetfindings` - This command fetches Hosts and Applications Findings information from RiskSense API. 
  * syntax - `| rsgetfindings client_id="123" asset_type="hostFindings" severity="critical" asset_id="123456" host_name="hostname" application_name="application name" operator="EXACT | WILDCARD" filters="field1=value1:OPEATOR1"`
  * Asset type can have hostFindings | applicationFindings value. Severity can have CRITICAL | HIGH | MEDIUM | LOW | INFO | TOTAL values. Operator can have EXACT | WILDCARD value.
* Note
  * The custom command will only run if the user has admin roles assigned or the user has `admin_all_objects` capability added.
  * For the custom command to fetch the account credentials, the user has to configure RiskSense Add-on for Splunk.
  * The custom command fetches the live records by making an API call when the search is run. If the Splunk instance is behind a proxy, the user needs to configure proxy settings in RiskSense Add-on for Splunk.

## UNINSTALL APP

To uninstall app, user can follow below steps: SSH to the Splunk instance Go to folder apps($SPLUNK_HOME/etc/apps) Remove the risksense_app_for_splunk folder from apps directory Restart Splunk

## SUPPORT

support@risksense.com
Copyright (C) 2020 RiskSense, Inc. All rights reserved.
