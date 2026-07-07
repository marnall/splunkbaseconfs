# RiskIQ Security Intelligence Service Add-on for Splunk

## This is an add-on powered by the Splunk Add-on Builder

## OVERVIEW

* The Add-on typically imports and enriches data from RiskIQ-AWS S3 Buckets. The RiskIQ Security Intelligence Service Add-on for Splunk will provide the below functionalities:
  * Collect data from RiskIQ-AWS S3 Buckets via REST endpoints and store them in Splunk indexes.
  * Categorize the data in different sourcetypes.
  * Parse the data and extract important fields.

* Author - RiskIQ Intelligence
* Version - 1.1.0
* Build - 1
* Prerequisites - RiskIQ-AWS AccessKeyId, RiskIQ-AWS SecretKey for data collection

## COMPATIBILITY MATRIX

* Browser: Google Chrome, Mozilla Firefox, Safari
* OS: Platform Independent
* Splunk Enterprise version: 8.1.X, 8.2.X
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

## RELEASE NOTES

### Version 1.1.0

* Upgraded AOB from v3.0.1 to v4.0.0
* Upgraded boto3 library from v1.13.5 to v1.20.46
* Upgraded botocore library from v1.16.5 to v1.23.46
* Upgraded jmespath library from v0.9.5 to v0.10.0
* Upgraded python-dateutil library from v2.8.1 to v2.8.2
* Upgraded s3transfer library from v0.3.3 to v0.5.0

### Version 1.0.0

* Data collection for Newly Observed Domain, Newly Observed Host, Malware Blacklist, Phishing Blacklist, Scam Blacklist, and Content Blacklist.


## END USER LICENSE AGREEMENT

https://www.riskiq.com/msa/

## OPEN SOURCE COMPONENTS AND LICENSES

Some of the components included in the RiskIQ Security Intelligence Service Add-on for Splunk are licensed under free or open-source licenses. We wish to thank the contributors to those projects.

* boto3 version 1.20.46 https://pypi.org/project/boto3/ (LICENSE https://github.com/boto/boto3/blob/develop/LICENSE)
* botocore version 1.23.46 https://pypi.org/project/botocore/ (LICENSE https://github.com/boto/botocore/blob/develop/LICENSE.txt)
* jmespath version 0.10.0 https://pypi.org/project/jmespath/ (LICENSE https://github.com/jmespath/jmespath.py/blob/develop/LICENSE.txt)
* python-dateutil version 2.8.2 https://pypi.org/project/python-dateutil/ (LICENSE https://github.com/dateutil/dateutil/blob/master/LICENSE)
* s3transfer version 0.5.0 https://pypi.org/project/s3transfer/ (LICENSE https://github.com/boto/s3transfer/blob/develop/LICENSE.txt)

## DOWNLOAD

* You can download RiskIQ Security Intelligence Service Add-on For Splunk from Splunkbase.

## RECOMMENDED SYSTEM CONFIGURATION

* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.
* [Hardware requirements reference](https://docs.splunk.com/Documentation/Splunk/8.0.3/Capacity/Referencehardware)

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This Add-On can be set up in two ways:

1) Standalone Mode: Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.  
2) Distributed Environment: Install Add-on on search head and Heavy forwarder (for REST API).

* Add-on resides on search head machine need not require any configuration here.
* Add-on needs to be installed and configured on the Heavy forwarder system.
* Execute the following command on Heavy forwarder to forward the collected data to the indexer.
  /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
* On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
* Add-on needs to be installed on search head for field extractions.

## INSTALLATION

Follow the below-listed steps to install an Add-on from the bundle:

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

OR

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

## CONFIGURATION

Follow the below steps for configuring RiskIQ Security Intelligence Service Add-on for Splunk.

* From the Splunk Home Page, click on RiskIQ Security Intelligence Service Add-on for Splunk. It will navigate to the Configuration section.
* In the Account tab, click on the `Add` button to configure a new Account.
* Enter the required details like Account Name (To uniquely identify accounts in Splunk), RiskIQ-AWS AccessKeyId, RiskIQ-AWS SecretKey, Data Types(types of data you want collect for this account) and click on Save to save the configuration.
* On the successful configuration of Account, Modular Inputs will be created automatically for selected input types in Disabled mode under the Inputs page.
* To use a proxy as part of the connection to RiskIQ-AWS S3, go to the Proxy tab and provide the required details. Don't forget to check the Enable option.
* To configure the Log Level, go to Logging tab, select the appropriate Log Level and save it.
* To manage the Modular Inputs, navigate to the Inputs section.
* If the user has successfully configured the Account, then Modular Inputs for selected Data Types have been created automatically and should appear here.
* User can enable/disable/edit/delete Modular Input by selecting specific Action.
* If the user wants to manually create RiskIQ Security Intelligence Service Modular Input, click on the `Create New Input` button provided on the top right.
* Specify all required parameters needed to configure inputs like Name, Interval, Index, Data Type, Collect Data For, RiskIQ-AWS Account, and click on Save to save the input configuration.

* NOTE: It is recommended to configure the Modular Input to initially collect data for the Last 1 Day to avoid search performance issues and to reduce the licensing cost.

## UPGRADATION

### Upgrade to v1.1.0
* Navigate to `RiskIQ Security Intelligence Service Add-on for Splunk -> Inputs`. Disable all the existing inputs.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Check the upgrade option.
* Select `Upload` and follow the prompts.
* Restart Splunk.

## TROUBLESHOOTING

### The input or configuration page is not loading.

* Check log file for possible errors/warnings: $SPLUNK_HOME/var/log/splunk/splunkd.log

### Account and Inputs are configured but data doesn't appear in Splunk search

* One of the possible causes for this problem is when a user has selected a different index to collect data. Splunk by default searches inside the `main` index.
* To add your custom index to default search, navigate to `Settings -> Roles -> Select the role -> Click the indexes tab -> Search for your custom index -> Check the Default checkbox -> Save`.

### Data is not getting collected in Splunk

* Go to the Search tab. Hit the following query `index=_internal sourcetype=tariskiqsecurityintelligenceservice:log` and check the results.
* Verify the configured Modular Inputs are valid and such files exist in the Bucket.
* Check the log file related to data collection is generated under `$SPLUNK_HOME/var/log/splunk/ta_riskiq_security_intelligence_service_riskiq_security_intelligence_service.log`.

##### Splunk Monitoring Console

* Check the Monitoring Console (>=v6.5) for errors.

### If the Splunk Instance is behind a proxy, Configure Proxy settings by navigating to RiskIQ Security Intelligence Service Add-on for Splunk -> Configuration -> Proxy

## DATA RETENTION POLICY

* To control the amount of data in particular index, use below settings in $SPLUNK_HOME/etc/apps/TA-riskiq-security-intelligence-service/local/indexes.conf for your index.  

  frozenTimePeriodInSecs = Time in seconds for which data should remain in index  
  maxDataSize = 750  
  maxHotBuckets = 1  

* Ex. Use below settings for keeping 1 day data in index `my_test_index`  
    [my_test_index]  
    frozenTimePeriodInSecs = 86400  
    maxDataSize = 750  
    maxHotBuckets = 1  

## UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/TA-riskiq-security-intelligence-service
* Remove $SPLUNK_HOME/var/log/splunk/**ta_riskiq_security_intelligence_service_riskiq_security_intelligence_service.log**
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance.

## SUPPORT

Email - splunk@riskiq.com

### Copyright 2016 - 2022 RiskIQ