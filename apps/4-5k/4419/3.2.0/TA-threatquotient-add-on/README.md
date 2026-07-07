# ThreatQuotient Add-on for Splunk

# OVERVIEW #
* This is an add-on powered by the Splunk Add-on Builder.
* The ThreatQuotient Add-on for Splunk is used to get indicators data from the ThreatQuotient platform.
* For the dashboard with ThreatQuotient data, please install ThreatQuotient App for Splunk.
* Author - ThreatQuotient Inc.
* Version - 3.2.0

# COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox
* OS: Linux (CentOs, Ubuntu) and Windows
* Splunk Enterprise version: 10.2.x, 10.0.x, 9.4.x and 9.3.x
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

# REQUIREMENTS #
* Appropriate credentials for collecting data from ThreatQuotient.
* Appropriate credentials of Splunk instance to ingest data into Splunk.

# RELEASE NOTES
## Version 3.2.0
* Added extraction for port value.
* Added CAC (Common Access Card) authentication support for account configuration.

## Version 3.1.0
* Added OAuth authentication support for account configuration.
* Added Response Page Size option in Input Configuration to define the number of indicators to retrieve per API request.
## Version 3.0.3
* Upgraded AOB to version 4.5.0.
## Version 3.0.2
* Added compatibility for Splunk 10.
## Version 3.0.1
* Fixed the data format causing issues for dashboard panels.
## Version 3.0.0
* Fixed cloud compatibility issues.
* Fixed data case sensitivity issue.
## Version: 2.8.0
* Upgraded Add-on Builder framework version to 4.2.0
* Fixed KV Store connectivity issue by replacing session key with credentials and requests library.
## Version: 2.7.0
* Upgraded Add-on Builder framework version to 4.1.3.
## Version: 2.6.0
* Moved "Alert Actions" and "Workflow Actions" to the ThreatQuotient App for Splunk
* Restricted initial data collection to last 90 days
* Removed usage of Proxy while checking KVStore status
* Removed the "Verify SSL Certificate" checkbox from the Configuration page. Navigate to the `$SPLUNK_HOME/etc/apps/TA-threatquotient-add-on/bin/threatq_const.py` and change VERIFY_SSL to False if certifiacte validation is not required.
## Version: 2.5.1
* Minor bug fix.
## Version: 2.5.0
* Minor bug fix.
* Migrated Threatquotient Add-on for Splunk with AOB version 4.1.0
## Version: 2.4.1
* Minor bug fix.
## Version: 2.4.0
* Minor bug fix.
* Updated data collection logic for custom field support.
## Version: 2.3.1 
* Allow user to run the workflow action without admin capability
## Version: 2.3.0
* Minor bug fix.
* Removed username and password dependency for kvstore data collection for the localhost.
* Providing support for the Malware Family attribute in kvstore
## Version: 2.2.0
* Collecting Indicators directly in KV store.
* Added option to collect historical data in the input configuration UI
* If indicators are deleted on ThreatQuotient server then it will be deleted from the KV store as well.
* Providing an option to the user to collect data into the index as well along with the KV store.
## Version: 2.1.0
* Made import timeout configurable from UI
* Added pagination for initial import in data collection
* Updated default interval time from 300 to 900
## Version: 2.0.0
* Made the add-on Python2 and Python3 compatible
## Version: 1.1.2
* Disabled InsecureRequestWarning error log in the splunkd log file.
## Version: 1.1.1
* Made fix in solnlib library.
## Version: 1.1.0
* Logging Enhancements
## Version: 1.0.1
* Added support for the verify SSL setting in the UI

# RECOMMENDED SYSTEM CONFIGURATION #
* Because this Add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT #
* This app has been distributed in two parts.
    * ThreatQuotient Add-on for Splunk, which listens for data from ThreatQuotient using REST API calls.
    * The ThreatQuotient App for Splunk for visualizing ThreatQuotient data.
* This app can be set up in two ways:
    * __Standalone Mode__:
        * Install the ThreatQuotient App for Splunk and ThreatQuotient Add-on for Splunk.
                * The ThreatQuotient App for Splunk uses the data collected by ThreatQuotient Add-on for Splunk and builds the dashboard on it.
    * __Distributed Environment__:
        * Install the ThreatQuotient App for Splunk on the search head. User needs to configure an account in ThreatQuotient App for Splunk.
        * Install only ThreatQuotient Add-on for Splunk on the heavy forwarder. User needs to configure account, needs to create data input, and needs to configure the Splunk KVStore Rest tab with the rest machine information to start data collection.
        * User needs to manually create an index on the indexer (No need to install ThreatQuotient App for Splunk or ThreatQuotient Add-on for Splunk on indexer).

# INSTALLATION OF APP #
* Follow the below-listed steps to install an Add-on from the bundle:
    * Download the App package.
    * From the UI navigate to Apps->Manage Apps.
    * In the top right corner select Install app from file.
    * Select Choose File and select the App package.
    * Select Upload and follow the prompts.

OR

* Directly from the Find More Apps section provided in Splunk Home Dashboard.

# UPGRADE

## General upgrade steps:
* Log in to Splunk Web and navigate to `Apps -> Manage Apps`.
* Click `Install app from file`.
* Click `Choose file` and select the ThreatQuotient Add-on installation file.
* Check the `Upgrade` checkbox.
* Click on `Upload`.
* Restart Splunk.

## Upgrade to V3.2.0
* Follow the below steps to upgrade the Add-on to 3.2.0

* Follow the `General upgrade steps` section.
* Navigate to the ThreatQuotient Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.

## Upgrade to V3.1.0
* Follow the below steps to upgrade the Add-on to 3.1.0

* Follow the `General upgrade steps` section.
* Navigate to the ThreatQuotient Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.

## Upgrade to V3.0.3
* Follow the below steps to upgrade the Add-on to 3.0.3

* Follow the `General upgrade steps` section.
* Navigate to the ThreatQuotient Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.

## Upgrade to V3.0.2
* Follow the below steps to upgrade the Add-on to 3.0.2

* Follow the `General upgrade steps` section.
* Navigate to the ThreatQuotient Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.

## Upgrade to V3.0.1
* Follow the below steps to upgrade the Add-on to 3.0.1

* Follow the `General upgrade steps` section.
* Navigate to the ThreatQuotient Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.

## Upgrade to V3.0.0
* Follow the below steps to upgrade the Add-on to 3.0.0

* Follow the `General upgrade steps` section.
* Navigate to the ThreatQuotient Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.

## Upgrade to V2.8.0
* Follow the below steps to upgrade the Add-on to 2.8.0

* Follow the `General upgrade steps` section.
* Navigate to the ThreatQuotient Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.

## Upgrade to V2.7.1
* Follow the below steps to upgrade the Add-on to 2.7.1

* Follow the `General upgrade steps` section.
* Navigate to the ThreatQuotient Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.

## Upgrade to V2.6.0
* Follow the below steps to upgrade the Add-on to 2.6.0

* Navigate to the ThreatQuotient Add-on for Splunk.
* From the Inputs page, disable already created input.
* From the `Settings` > `Searches, Reports and Alerts`, delete already created alerts under this App.
* Follow the `General upgrade steps` section.
* Navigate to the ThreatQuotient Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with the required fields.

## Upgrade to V2.5.1
* Follow the below steps to upgrade the Add-on to 2.5.1

* Follow the `General upgrade steps` section.
* Navigate to the ThreatQuotient Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.

## Upgrade to V2.5.0
* Follow the below steps to upgrade the Add-on to 2.5.0

* Follow the `General upgrade steps` section.
* Navigate to the ThreatQuotient Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.

## Upgrade to V2.4.1
Follow the below steps to upgrade the Add-on to 2.4.1

* Follow the `General upgrade steps` section.
* Go to the apps list and open ThreatQuotient Add-on for Splunk.

## Upgrade to V2.4.0
Follow the below steps to upgrade the Add-on to 2.4.0

* Follow the `General upgrade steps` section.
* Go to the apps list and open ThreatQuotient Add-on for Splunk.
* Verify that only one input is configured under the Inputs tab otherwise later on some discrepancies will be noticed in data collection. So keep only one input configured.

## Upgrade to V2.3.1
Follow the below steps to upgrade the Add-on to 2.3.1

* Follow the `General upgrade steps` section.
* Go to the apps list and open ThreatQuotient Add-on for Splunk.
* Verify that only one input is configured under the Inputs tab otherwise later on there would be some discrepancies will be noticed in data collection. So keep only one input configured.
* Go to Configuration > Splunk KVStore Rest tab and provide the credentials of the Splunk Instance on which the user wants to collect the data. (Note: Make sure the ThreatQAppforSplunk v2.1.0 or above is installed on a machine where the user wants to collect the data in lookups)

# CONFIGURATION OF APP #
* Navigate to ThreatQuotient Add-on for Splunk, click on "Configuration", go to "Account" tab and fill in "Authorization Type", "Server URL", "Username", "Password", "Client ID" and "Client Secret".
* Navigate to ThreatQuotient Add-on for Splunk, click on "Configuration", go to "Splunk KVStore Rest" tab and fill in "Splunk Username", "Splunk Password", "Splunk Rest Host URL" and "Port".
* Navigate to ThreatQuotient Add-on, click on "Inputs", click on "Create New Input" and fill the "Name", "Interval", "Index", "Export ID", "Export Token", "Export Hash", "Threshold Indicator Score" and "Indicator Status". Optionally enable the "Enable Index" checkbox to index data into the selected index. It is mandatory to enable the "Pull All Indicators" checkbox on input creation. Enabling this checkbox later using input edit option will cause input to collect all indicators from ThreatQuotient as if it was newly created (Note: "Pull All Indicators" checkbox when enabled will collect all indicators including historical indicators and when disabled it will use the differential import and only collect modified/new indicators. This checkbox value will change its state to disabled once all indicators are pulled during the first input invocation. Hence from the second invocation, it will use differential import.)
* NOTES: 
    * After adding the custom fields, if user wants to collect the same fields for existing data in master lookup then user has to do the data collection again by enabling “Pull All Indicators”. 
    * By default the value for "Verify SSL" will be True. To change that, navigate to the splunk backend at `$SPLUNK_HOME/etc/apps/TA-threatquotient-add-on/bin/threatq_const.py` and change the value to False.


* Restart the Splunk.

# TROUBLESHOOTING #
* To troubleshoot ThreatQuotient Add-on for Splunk please check $SPLUNK_HOME/var/log/splunk/ta_threatquotient_add_on_\*.log\* file.
* To check the data collected by data collection in index use query like "index=<your_index_name> sourcetype=threatq:indicators"
* To check the data collected by data collection in master_lookup use query like "|inputlookup master_lookup".
* To check the data collected by data collection in threatq_indicator_types and threatq_indicator_status, use queries like "|inputlookup threatq_indicator_types" and "|inputlookup threatq_indicator_status" respectively.
* If there are some discrepancies or unusual behavior noticed in master_lookup then verify that only one input is configured in ThreatQuotient Add-on for Splunk. If more than one inputs are configured then delete all other configured inputs and keep only one input for the data collection.
* If user is getting "Not able to authenticate using provided configuration parameters" error, check if the SSL Validation is done properly. If it's not required, update the value for "Verify SSL" from backend at `$SPLUNK_HOME/etc/apps/TA-threatquotient-add-on/bin/threatq_const.py`.
* If the User has marked Verify SSL Certificate as True in Splunk KVStore Rest tab then User needs to consider the value of Splunk Rest Host URL while generating an SSL certificate. (e.g.1.<ip_address> provided in Splunk Rest Host URL, then use ip_address while generating SSL Certificate, e.g.2 "localhost" provided then use localhost while generating SSL Certificate)
* If User upgrade the ThreatQuotient Add-on for Splunk or changing the Username, Password, Port of the Splunk Instance then the data collection will be stopped So, user needs to reconfigure the Splunk KVStore Rest tab.
* If user is not able to access some of the functionality of threatq then refer the below table of roles and access by threatq functionality.

| Functionality| Admin  | Power  | Splunk_System_Role | User | can_delete | ess_user | ess_analyst | ess_admin |
|--------------|------------------| ---------------- | ----------------| ----------------------| -------------------- | -------------------------| ------------------------------------ | -------------------------------- |
|Configure Account | create,edit,view,clone,delete | --- | create,edit,view,clone,delete | ---| ---| ---| ---| create,edit,view,clone,delete |
|Configure Input | create,edit,view,clone,delete | --- | create,edit,view,clone,delete | ---| ---| ---| ---| create,edit,view,clone,delete |
| Data Collection | enable,disable | enable,disable | enable,disable | enable,disable | --- | enable,disable | enable,disable | enable,disable |
| Configure Setup Dashboard | edit,view | view | edit,view | view | ---| view | view| edit,view |
| Use of Raw matching saved searches | create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run|
| Use of Data model saved searches | create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run|
| Use of ES related saved searches | create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run| create,edit,view,delete,run|

* If user is not able to collect the custom attributes into lookup, then user needs to check if the attributes are of the following formats. Only these formats are supported:

*       Attributes: [
            {
                name: "attr1",
                value: "val1"
            },
            {
                ...
            },
            ...
        ]
            where,
                - "att1" is attribute name.
                - "val1" is attribute value.


*       Attributes: [
            {
               "attr1": "val1"
            },
            {
                ...
            },
            ...
        ]
            where,
                - "att1" is attribute name.
                - "val1" is attribute value.

*       attributes: [
            {
                name: "attr1",
                value: "val1"
            },
            {
                ...
            },
            ...
        ]
            where,
                - "att1" is attribute name.
                - "val1" is attribute value.


*       attributes: [
            {
               "attr1": "val1"
            },
            {
                ...
            },
            ...
        ]
            where,
                - "att1" is attribute name.
                - "val1" is attribute value.
# SAMPLE EVENT GENERATOR #
* The ThreatQuotient Add-on for Splunk comes with sample data files, which can be used to generate sample data for testing. To generate sample data, it requires the SA-Eventgen application.
* Typically eventgen is disabled for the TA and it will generate sample data at an interval of 300 seconds. You can update this configuration from eventgen.conf file available under $SPLUNK_HOME/etc/apps/TA-threatquotient-add-on/default/.

# LIMITATION #
* ThreatQuotient Add-on for Splunk does not support IPv6 address in the proxy configuration.
* User needs to Provide the Splunk credentials in TA-threatquotient-add-on > Configuration > Splunk KVStore Rest tab to start the data collection on rest host.
* ThreatQuotient Add-on for Splunk Only allowed to configure one input from the UI.

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/TA-threatquotient-add-on
* Remove $SPLUNK_HOME/var/log/splunk/**ta_threatquotient_add_on_threatq_indicators.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_threatquotient_add_on_utils.log**

* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# BINARY FILE DECLARATION
* markupsafe - MarkupSafe implements a text object that escapes characters so it is safe to use in HTML and XML. https://pypi.org/project/MarkupSafe/.

# SUPPORT #
* Support Offered: Yes
* Support Email: support@threatq.com

### Copyright (c) 2026 ThreatQuotient, Inc.