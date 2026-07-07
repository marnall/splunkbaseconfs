# RiskSense Addon For Splunk

## This is an add-on powered by the Splunk Add-on Builder

## OVERVIEW

* The Add-on typically imports and enriches data from Risksense API, creating a rich data set ready for direct analysis or use in an App. The RiskSense Add-on for Splunk will provide the below functionalities:
  * Collect data from RiskSense via REST endpoints and store in Splunk indexes
  * Categorize the data in different sourcetypes
  * Parse the data and extract important fields

* Author - RiskSense
* Version - 1.1.0
* Build - 1
* Prerequisites - Risksense API Token, Client Name for data collection
* Compatible with:
  * Splunk Enterprise version: 8.0.x, 7.3.x, 7.2.x and 7.1.x
  * OS: Platform independent

## END USER LICENSE AGREEMENT

https://risksense.com/customer-agreements/

## OPEN SOURCE COMPONENTS AND LICENSES

Some of the components included in RiskSense Add-on for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* croniter version 0.3.25 https://pypi.org/project/croniter/ (LICENSE https://github.com/kiorky/croniter/blob/master/docs/LICENSE)

## RELEASE NOTES

* Version 1.1.0
  * Fixed pagination in clients data collection.

## RECOMMENDED SYSTEM CONFIGURATION

* Splunk forwarder system should have 12 GB of RAM and a six-core CPU to run this Technology Add-on smoothly.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This Add-On can be set up in two ways:

1) Standalone Mode: Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup
2) Distributed Environment: Install Add-on on search head and Add-on on Heavy forwarder (for REST API).

* Add-on resides on search head machine and accounts need to be configured here.
* Add-on needs to be installed and configured on the Heavy forwarder system.
* Execute the following command on Heavy forwarder to forward the collected data to the indexer.
  /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
* On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
* Add-on needs to be installed on search head for CIM mapping

## INSTALLATION

Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

## UPGRADE

Follow the below steps when upgrading from RiskSense Add-on for Splunk

* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Check the upgrade option.
* Select `Upload` and follow the prompts.
* Restart Splunk.

### UPGRADE TO v1.1.0

* After following the above steps, from the Splunk Home Page, click on RiskSense Add-on for Splunk and navigate to the Input section.
* Click on Actions and disable all the inputs.
* Navigate to Configuration section and add a new account or edit the already created account.
* The above step is necessary to refresh the clients information in configuration files.
* Edit the input by selecting the newly created account.
* Enable the input to collect the data.

## CONFIGURATION

Follow the below steps for configuring RiskSense Add-on for Splunk

* From the Splunk Home Page, click on RiskSense Add-on for Splunk and navigate to the Configuration section.
* In the Account tab, click on the Add button to configure a new Account.
* Enter the required details like Account Name (To uniquely identify accounts in splunk), RiskSense Platform URL, Client Name and API Token.
* The user can specify comma separated list of client names to collect the data for. If the user specifies 'All', then data for all the clients will be collected.
* Click on Save to save the configuration.
* After an Account is configured, the user should navigate to the Input tab.
* Click on the Add button to configure input for data collection.
* Specify all required parameters needed to configure input like name, interval, index, Account, Type (Hosts/Apps), Filters and Page Size.
* Filters can be specified in the format of field1=value1:OPERATOR1;field2=value2:OPERATOR2 and likewise.
* If the specified filters are invalid, users will not be able to save the configuration.
* Click on Save to save the input configuration.

## TROUBLESHOOTING

### The input and configuration pages are not loaded of the add-on

* Check log file for possible errors/warnings: $SPLUNK_HOME/var/log/splunk/splunkd.log

### Account and input are configured but data doesn't appear in Splunk search or dashboards

* One of the possible causes for this problem is when a user has selected a different index to collect data. Splunk by default searches inside the `main` index.
* To add your custom index to default search, navigate to `Settings -> Roles -> Select the role -> Click the indexes tab -> Search for you custom index -> Check the Default checkbox -> Save`

### Data is not getting collected in Splunk

* Go to Search tab. Hit the following query `index="_internal" sourcetype="tarisksense:log"` and check the results.
* Verify the filters configured during data collection are valid and such events exist on the platform.
* Check the log file related to data collection is generated under `$SPLUNK_HOME/var/log/splunk/ta_risksense_risksense.log`.
* To get the detailed logs, in the Splunk UI, navigate to RiskSense Add-on For Splunk. Click on Configuration and go to the Logging tab. Select the Log level to DEBUG.
* Disable/Enable the input to re-collect the data.
* Check the logs. They will be more verbose and will give the user insights on data collection.

### Data for a particular client is not getting collected

* Verify you have entered the client name in the Account configuration section.
* If some client is added in the RiskSense Platform after configuring account in Splunk, User needs to update that account with the new client name.

### No client id found corresponding to given client name

* Verify the client name entered is same as the client name available in the RiskSense platform.
* If you don't have any clients configured in the Platform, you will need to configure one.

### Error while configuring input

* Verify the fields used in filters. The filters only work if API supports that particular field.
* Check your configured API token has not been revoked the access to collect data.

### If the Splunk Instance is behind a proxy, Configure Proxy settings by navigating to RiskSense Add-on for Splunk -> Configuration -> Proxy

## UNINSTALL APP

To uninstall app, user can follow below steps: SSH to the Splunk instance Go to folder apps($SPLUNK_HOME/etc/apps) Remove the TA-risksense folder from apps directory Restart Splunk

## SUPPORT

support@risksense.com
Copyright (C) 2020 RiskSense, Inc. All rights reserved.
