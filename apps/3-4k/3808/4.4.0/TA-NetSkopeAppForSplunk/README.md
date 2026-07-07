# Splunk Technology Add-on for Netskope

## This is an add-on powered by the Splunk Add-on Builder

## OVERVIEW

* The Add-on typically imports and enriches data from Netskope API, creating a rich data set ready for direct analysis or use in an App. The Netskope Add-on for Splunk will provide the following functionalities:
    * Collect data from Netskope via REST endpoints and store it in Splunk indexes
    * Categorize the data in different sourcetypes
    * Parse the data and extract important fields

* Author - Netskope, Inc.
* Version - 4.4.0
* Build - 3

* Compatible with:

    * Prerequisites - Netskope API Token for data collection
    * Splunk Enterprise version: 10.2.x, 10.0.x, 9.4.x, and 9.3.x
    * Python version: Python 3.7 and Python 3.9
    * OS: Platform independent
    * Browser: Google Chrome, Firefox

## PREREQUISITES:


### Events & Alerts Input
* If the Netskope and Splunk admin wants to leverage API v2, they should create a new v2 API token that is fully entitled with every read scope (Refer to section #SUPPORTED TOKENS AND REQUIRED PERMISSIONS).

### Orchestration Actions (Populate URL list or Filehash list)
* File Hash Alert Action supports only V1 token which doesn't require setting any scope.
* To use the URL list, Netskope admin will need to increase the APIv2 token's scope to include read AND write scope (Refer to section #SUPPORTED TOKENS AND REQUIRED PERMISSIONS).


### Orchestration Actions (Quarantine file)
* Quarantine File Alert Action requires Microsoft Azure RBAC of atleast 'Contributor' level to move files from one container to another.


## END USER LICENSE AGREEMENT

https://www.netskope.com/software-eula

## OPEN SOURCE COMPONENTS AND LICENSES

Some of the components included in the Netskope Add-on for Splunk are licensed under free or open-source licenses. We wish to thank the contributors to those projects.

* croniter version 0.3.31 https://pypi.org/project/croniter/ (LICENSE https://github.com/kiorky/croniter/blob/master/docs/LICENSE)
* PySocks version 1.7.1 https://pypi.org/project/PySocks/ (LICENSE https://github.com/Anorov/PySocks/blob/master/LICENSE)
* google-cloud-pubsublite version 1.4.2 https://pypi.org/project/google-cloud-pubsublite/ (LICENSE https://github.com/googleapis/python-pubsublite/blob/main/LICENSE)
* azure-storage-blob version 12.18.2 https://pypi.org/project/azure-storage-blob/ (LICENSE https://github.com/Azure/azure-sdk-for-python/blob/main/LICENSE)
* netskopesdk version https://pypi.org/project/netskopesdk/

## DOWNLOAD

* Download Netskope Add-on For Splunk at https://splunkbase.splunk.com/app/3808/.
* Download Netskope App For Splunk at https://splunkbase.splunk.com/app/3414/.

## RECOMMENDED SYSTEM CONFIGURATION

* Refer to the Splunk Enterprise system requirements: [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements)

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This Add-On can be set up in two ways:

1) Standalone Mode: Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.  
2) Distributed Environment: Install Add-on on search head and Heavy forwarder (for REST API).

* Add-on resides on the search head machine and does not require any configuration here.
* Add-on needs to be installed and configured on the Heavy forwarder system.
* Execute the following command on Heavy Forwarder to forward the collected data to the indexer.
  $SPLUNK_HOME/bin/splunk add forward-server <indexer_ip_address>:9997
* On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
* Add-on needs to be installed on the search head for CIM mapping

**NOTE:** Here $SPLUNK_HOME is the absolute path where Splunk is installed.


## SUPPORTED TOKENS AND REQUIRED PERMISSIONS

* Ensure you are configuring inputs or alert actions with an account configured with tokens as shown below.

    * Event types: Connection, Application, Network, Audit, Infrastructure, Incident, Endpoint
  
    * Alert Types: compromisedcredential, ctep, dlp, malsite, malware, policy, quarantine, remediation, securityassessment, uba, watchlist, device, content

| Input Name / Alert Action    | Supported Tokens / Key                                     |
| ---------------------------- | ---------------------------------------------------------- |
| Events (Iterator)            | V2 Token                                                   |
| Alerts (Iterator)            | V2 Token                                                   |
| Events (Multi Iterator)      | V2 Token                                                   |
| Clients (Iterator)           | V2 Token                                                   |
| Clients                      | V1 Token                                                   |
| URL List Alert Action        | V1/V2 Token (V2 Token will be used if both are configured) |
| File Hash Alert Action       | V1 Token                                                   |
| Quarantine File Alert Action | Azure RBAC of 'Contributor' role                           |

* If V2 Token is configured, ensure it has sufficient endpoint permissions for respective inputs or alert actions as listed in the table.

| Input Name / Alert Action | Endpoint Permissions | Required Permissions |
| --- | --- | --- |
| Events (Iterator)  | /api/v2/events/dataexport/events/*  |  Read  |
| Alerts (Iterator)  | /api/v2/events/dataexport/events/audit, /api/v2/events/dataexport/events/alert, /api/v2/events/dataexport/alerts/*  |  Read  |
| Events (Multi Iterator) | /api/v2/events/dataexport/events/audit |  Read  |
| |  /api/v2/events/dataexport/iterator/*  |   Read, Write  |
| Clients (Iterator) | /api/v2/events/dataexport/events/audit |  Read  |
| |  /api/v2/events/dataexport/iterator/*  |   Read, Write  |
| URL List Alert Action  | /api/v2/policy/*  |  Read  |

**NOTE:**

* Here "/api/v2/events/dataexport/events/*" means all endpoints starting with the "/api/v2/events/dataexport/events/" prefix.
* To update the V2 Token permission, login to the netskope portal and then navigate to Settings > Tools > REST API v2.
* V1 Token doesn't require any additional steps of adding permissions.
* When configuring "Token V2" on the account page, "/api/v2/events/dataexport/events/audit" or "/api/v2/events/data/page" endpoint permissions will be required for Iterator and Deprecated inputs, respectively.
* To use the "Email Notification" feature with a personal Gmail account, an app password is required for that Gmail account. To setup the App Password, follow these steps: https://support.google.com/accounts/answer/185833?hl=en

## INSTALLATION

Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## UPGRADE

### General Upgrade Steps
* Before upgrading, disable all the inputs.
* Take a backup of $SPLUNK_HOME/etc/apps/TA-NetSkopeAppForSplunk/local directory. (To revert in case of any upgrade failure)
* Upgrade TA-NetSkopeAppForSplunk
* Download the App package.
* From the UI navigate to Apps->Manage Apps.
* In the top right corner select Install app from file.
* Select Choose File and select the App package.
* Select the checkbox "Upgrade app".
* Select Upload and follow the prompts.
* After the Upgrade is done successfully, reenable the existing inputs.

**NOTE:**

* During the change in event header format (from format-1 to format-2/3) from the Netskope platform side, if any input interruption action (input disable / splunk restart) occurs then there might be a chance of data duplication because messages are not processed and acknowledged in sequence.
* If the user updates the token of the configured account and input is enabled then it might take approx 30min time to consider the new token. To pick up the token immediately, disable and enable the input.
* If you are upgrading using the Splunk deployment server then please follow the below steps to avoid issues related to losing existing configuration (local directory) Link: https://docs.splunk.com/Documentation/Splunk/9.0.3/Updating/Excludecontent
* If you face any UI rendering issues after the upgrade then bump the Splunk by hitting the "<hostname>/en-US/_bump" URL (after logging in to Splunk web) and clicking on the "Bump version" button.

### Upgrading to v4.0.0 and above
#### From v3.4.0 and above
* No additional upgrade steps are required. follow the "General Upgrade Steps" section mentioned above.

#### From v3.3.1 and lower
* Additional upgrade steps are only required for "Web Transaction V2" input. For the rest of the inputs, follow the "General Upgrade Steps" section mentioned above.

**Steps:** (Before upgrading) (Only for "Web Transaction V2" input)
1. Provide the Netskope V2 token with the '/api/v2/events/token/transaction_events' endpoint's permission.
2. Either update the current account used for the "Web Transaction V2" input or configure a new account with a V2 token having above-mentioned endpoint's permission.
3. If a new account is created, then update the "Web Transaction V2" input's 'Netskope Account' field with the new account created.
4. Follow the "General Upgrade Steps" section mentioned above.

**NOTE:**

* Existing "Events (Deprecated)" and "Alerts (Deprecated)" inputs are removed in v3.7.0. Migrate deprecated inputs to iterator inputs.

## Steps: (Before upgrading) (Only for "Events (Deprecated)" and "Alerts (Deprecated)" input)
1. Follow the below steps to migrate deprecated inputs (i.e."Events (Deprecated)" and "Alerts (Deprecated)") to iterator inputs (i.e."Events (Iterator)" and "Alerts (Iterator)") which is available from v3.1.0 onwards:

  * Run the Splunk search (on the "search head" component in case of the distributed environment) mentioned for respective input in the following table and copy the date from the "Start DateTime" field of the search result:

| Deprecated Input    | Iterator Input    | Splunk Search |
| ------------------- | ----------------- | ------------- |
| Events (Deprecated) | Events (Iterator) | ``` | tstats max(_indextime) as IndexTime max(_time) as Time where index="*" AND source="netskope" by source        | eval "Start DateTime" = coalesce(Time, IndexTime) | fieldformat "Start DateTime"=strftime('Start DateTime',"%Y-%m-%dT%H:%M:%SZ") | fields - IndexTime Time ``` |
| Alerts (Deprecated) | Alerts (Iterator) | ``` | tstats max(_indextime) as IndexTime max(_time) as Time where index="*" AND source="netskope_alerts" by source | eval "Start DateTime" = coalesce(Time, IndexTime) | fieldformat "Start DateTime"=strftime('Start DateTime',"%Y-%m-%dT%H:%M:%SZ") | fields - IndexTime Time```  |

  * Add the copied DateTime value in the "Start DateTime" field while the configuration of iterator input.

**NOTE:**

* While running the search, make sure that the selected time range should have data collected in the index. If not then expand the time range.
* While running the search, make sure that the selected Splunk "Time zone" should be "(GMT) Greenwich Mean Time". To update the "Time zone" go to Administrator > Preferences > Time zone
* While switching deprecated inputs (i.e."Events (Deprecated)" and "Alerts (Deprecated)") to iterator inputs (i.e."Events (Iterator)" and "Alerts (Iterator)"), make sure that both iterator and deprecated input are not running in parallel.

**NOTE:**

* If you face any UI rendering issues after the upgrade then bump the Splunk by hitting the "<hostname>/en-US/_bump" URL (after logging in to Splunk web) and clicking on the "Bump version" button.
* If any data is missed during the time of migration for inputs of type "Alerts", "Events" & "Clients", please create the same input with "Collection Type" as "Historical", which will ask for Start & End DateTime for which you want to collect historical data.

## CONFIGURATION

Follow the below steps for configuring Netskope Add-on for Splunk

* From the Splunk Home Page, click on Netskope Add-on for Splunk and navigate to the Configuration section.
* In the Account tab, click on the `Add` button to configure a new Account.
* Enter the required details like Account Name (To uniquely identify accounts in Splunk), Netskope Tenant URL, Netskope API Token, and click on Save to save the configuration.
* To use Quarantine File Alert Action, a Storage Account is needed which can be configured from the Storage Account tab.
* In the Storage Account tab, click on the `Add` button to configure a new Account.
* Enter required details like Account Name (To uniquely identify storage accounts in Splunk), Connection String, and Destination container name.
* To use a proxy as part of the connection to Netskope, go to the Proxy tab and provide the required details. Don't forget to check the Enable option.
* To configure the Log Level, go to the Logging tab.
* To change the Base Event Type, go to the Add-on Settings tab. It will be the base search for all event types(All the Dashboards of Netskope App for Splunk will refer to this Base Event Type to populate the data in the Dashboards)
* To use the Email Notification feature, configure the details in the "Email Notification" tab.
* Enter required details like Email Address(es), Notify After No Logs Received, and valid SMTP Server.
* To manage the Modular Inputs, navigate to the Inputs section.
* User can configure/enable/disable/edit/delete Modular Input by selecting specific Action.
* If the user wants to manually create specific(Events/Alerts/Clients) Modular Input, click on the `Create New Input` button provided on the top right.
* Specify all required parameters needed to configure inputs like Name, Interval, Index, Netskope Account, Start Date Time, Query, Event Types, Alert Types, etc, and click on Save to save the input configuration.

  * The significance of each field of "Events (Iterator)" is explained below:

| Input Parameters | Type        | Description                                                                          |
| ---------------- | ----------- | ------------------------------------------------------------------------------------ |
| Name             | Textbox     | The unique name for input                                                            |
| Interval         | Textbox     | Modular Input invocation in Seconds or Cron                                          |
| Index            | Textbox     | The index in which data will be collected                                            |
| Netskope Account | Dropdown    | Account configured from "Accounts" Page                                              |
| Start DateTime   | Textbox     | Only events that occur after this date will be fetched from Netskope.                |
| End DateTime     | Textbox     | Only events that occur till this date will be fetched from Netskope.                 |
| Event Types      | Multiselect | Types of events to collect.                                                          |
| Refine Data      | Dropdown    | Refine the data by manually specifying the fields you'd like to include or exclude.  |
| Fields to Include| Textbox     | Enter comma seprated fields to Include.                                              |
| Fields to Exclude| Textbox     | Enter comma seprated fields to Exclude.                                              |

  * The significance of each field of "Alerts (Iterator)" is explained below:

| Input Parameters | Type        | Description                                                                          |
| ---------------- | ----------- | ------------------------------------------------------------------------------------ |
| Name             | Textbox     | The unique name for input                                                            |
| Interval         | Textbox     | Modular Input invocation in Seconds or Cron                                          |
| Index            | Textbox     | The index in which data will be collected                                            |
| Netskope Account | Dropdown    | Account configured from "Accounts" Page                                              |
| Start DateTime   | Textbox     | Only events that occur after this date will be fetched from Netskope.                |
| End DateTime     | Textbox     | Only events that occur till this date will be fetched from Netskope.                 |
| Alert Types      | Multiselect | Types of alert to collect.                                                           |
| Refine Data      | Dropdown    | Refine the data by manually specifying the fields you'd like to include or exclude.  |
| Fields to Include| Textbox     | Enter comma seprated fields to Include.                                              |
| Fields to Exclude| Textbox     | Enter comma seprated fields to Exclude.                                              |
                                                     
  * The significance of each field of "Events (Multi Iterator)" is explained below:

| Input Parameters | Type        | Description                                                                          |
| ---------------- | ----------- | ------------------------------------------------------------------------------------ |
| Name             | Textbox     | The unique name for input                                                            |
| Index            | Textbox     | The index in which data will be collected                                            |
| Netskope Account | Dropdown    | Account configured from "Accounts" Page                                              |
| Event Types      | Dropdown    | Type of events to collect.                                                          |

  * The significance of each field of "Clients (Iterator)" is explained below:

| Input Parameters | Type        | Description                                                                          |
| ---------------- | ----------- | ------------------------------------------------------------------------------------ |
| Name             | Textbox     | The unique name for input                                                            |
| Index            | Textbox     | The index in which data will be collected                                            |
| Netskope Account | Dropdown    | Account configured from "Accounts" Page                                              |
                                                     

**NOTE:**

* The "Events (Iterator)", "Alerts (Iterator)", "Events (Multi Iterator)" and "Clients (Iterator)" inputs only support the v2 token.
* In the "Alerts (Iterator)" input, select the specific alert type instead of "All" to get detailed alert events.
* The "Alerts (Iterator)" input may cause resource usage to increase if separate alert types are selected since the threading mechanism will collect all types of alerts simultaneously.
* Clients (Iterator) and Events (Multi Iterator) Input supports **real-time data collection only**. Historical data collection is **not supported**.
* Events (Multi Iterator) Input is designed for customers with very high volume of data generation. It currently supports data collection for Page, Application, Network
* If you are collecting data in the custom index then Don't forget to update the Base Event Type under Add-on Settings of Configuration Section
e.g. index=main OR index=custom_index_1 OR index=custom_index_2

## CONFIGURATION OF EMAIL NOTIFICATION

Follow the below steps for configuring Email Notification

* From the Splunk Home Page, click on Netskope Add-on for Splunk and navigate to the Configuration section.
* Go to the 'Email Notification' tab.
* Enter required details like Email Address(es), Notify After No Logs Received and valid SMTP Server.
* Select the `Enable` checkbox and click on Save to save the configuration.
* To suppress the Email notification, select the `Enable Throttle` checkbox and enter the duration in the `Suppress triggering for` field till which you want to suppress the email notification.
* SMTP Server configuration guide: https://docs.splunk.com/Documentation/Splunk/9.1.2/Alert/Emailnotification#Configure_email_notification_for_your_Splunk_instance

**NOTE:**

* Valid configuration of the SMTP server is required for sending the Email notification.

### CONFIGURABLE PARAMETERS FOR EMAIL NOTIFICATION

The Email Notification contains the following parameters which can be configured based on the user preference. The description and the default value for all the parameters are as follows:

| Parameter                     | Description                                                                                | Default Value | Minimum Allowed Value  |
| ------------------------------| -------------------------------------------------------------------------------------------| --------------| -----------------------|
| Enable                        | Whether the email notification should be enabled or not?                                   | -             | -                      |
| Email Address(es)             | Comma-separated list Email Address to send email notification.                             | -             | -                      |
| Notify After No Logs Received | Duration (in hours) if no data collected for this duration triggers an email notification. | 24            | 1                      |
| SMTP Server                   | Configured SMTP Server name.                                                               | -             | -                      |
| Additional Message            | Additional message to send in email body in notification.                                  | -             | -                      |
| Enable Throttle               | Whether the email notification suppression should be enabled or not?                       | -             | -                      |
| Suppress triggering for       | Duration (in hours) to suppress Email notification.                                        | 24            | 1                      |


## ALERT ACTION

Three types of Alert Actions

* Netskope File Hash Alert Action
* Netskope URL Alert Action
* Netskope Quarantine File Alert Action

These Alert Actions can be used to either add or remove items from the lists.

# For Netskope File Hash Alert Action and Netskope URL Alert Action:

* When configuring the Alert Action, User needs to select Netskope Account and Index, Users can choose action to take as either Add or Remove, Provide List Name (it should exist on Netskope platform) and Field Name of the search result that contains the value to update into a list.
* While creating alert action, If you have selected an index other than cim_modactions in UI then please update the list of the index in the search query of stanza netskope_action_modresult in eventtypes.conf
e.g index IN ("cim_modactions", "main", "alertactions")
* Example saved searches for these Alert Action is provided in disabled mode. Users can take references from these to configure the Alert Action.
  * Sample Netskope File Hash Alert Action
  * Sample Netskope URL Alert Action

Warning:

* If you want to use the API v2 token then configure the API v2 token in the existing account which is used in the URL list alert action. If a new account is created for the existing URL list alert action, then the old URL list will be removed & it will start filling from that point.

# For Netskope Quarantine File Alert Action:

* When configuring the Alert Action, the User needs to select Storage Account (in which the desired destination container is configured).


**NOTE:**

* URL List Alert Action can be used with both API v1 & v2 tokens. API v2 token will be preferred if both are configured in an account.
* File Hash list alert action doesn't support API v2 token.
* For Quarantine file alert action Microsoft Azure account with minimum Role Backed Access of 'Contributor' is required.


## KNOWN ISSUES

* For inputs (Events & Alerts Input) with real-time data collection will try to collect data as realtime as possible, but if it lags due to a large amount of data in a specific time range and lagging time reaches to 1 hour then data collection will reset back to last 30 seconds and data during that 1 hour will not be collected.
  - To collect that 1-hour data separately, run below Splunk's search query which will give you skipped time ranges with input type, starttime, endtime, and sub-types information. Using these, create an input with collection type as historical where you can specify Start Time & End Time. 
  ```index=_internal source="*netskope*" ERROR message=reset_checkpoint | eval input=if(match(source, "netskope.log"), "Events", "Alerts") | table input, starttime, endtime, types```

* URL List alert action reports `500 - Internal Server Error` error in the log file if API token v2 is used & a large number of URLs were published in the single API call. Until it is fixed in a future release, use the API v1 token or make sure that the configured alert action doesn't push a large number
of URLs in a single invocation.

* In the List view of Splunk v8.x.x, integer values are getting rounded off when they reach the maximum integer value: Please note that this is only a view issue from the Splunk end. It is fixed in Splunk v9.x.x


## TROUBLESHOOTING


### Getting 403 errors while collecting data from Events (Iterator)/ Alerts (Iterator) inputs
* Make sure that the configured token has sufficient permission as listed in the section Details > "SUPPORTED TOKENS AND REQUIRED PERMISSIONS"
* For the V2 token, make sure that REST API status is enabled on the Netskope platform (Settings > Tools > Rest API V2 )
* If still doesn't work then renew the token (go to Settings > Tools > Rest API V2)

### For the V2 token, getting 401 errors while collecting data from Events (Iterator)/ Alerts (Iterator) inputs
* Make sure that the configured token is not expired if so then update the expiration time in the Netskope platform (Settings > Tools > Rest API V2 )
* If still doesn't work then renew the token (go to Settings > Tools > Rest API V2)

### Data collection is not working even after updating the newly generated token
* For all the inputs, make sure you disable and enable the existing running inputs so it starts using the updated token.

### The input or configuration page is not loading.

* Check the log file for possible errors/warnings: $SPLUNK_HOME/var/log/splunk/splunkd.log

### URL List or File Hash List is not getting updated even after the execution of the alert action is completed.

* Make sure the provided list exists on the Netskope Platform.

* Check the log file for possible errors/warnings: 
  * $SPLUNK_HOME/var/log/splunk/netskope_file_hash_modalert.log
  * $SPLUNK_HOME/var/log/splunk/netskope_url_modalert.log

* If you get any error log stating that the list size reached to maximum allowed size, remove unnecessary elements from the list as Netskope allows a maximum size of the list to be approximately 8 MB.
* If you get any network-related error log (like Timeout, Unreachable or Max retry exceeds) then revalidate the configured Proxy and Netskope Account.

* Note: For ease in troubleshooting, you can use the Alert Action Dashboard in "Netskope App For Splunk" which will show recent errors and other statistics.

### Splunk ES is not getting any events generated by Alert Action execution.

* Select "notable" as an index parameter while configuring Alert Action, because many Splunk ES functionalities related to Adaptive Response work on the "notable" index only.

### Account and Inputs are configured but data doesn't appear in Splunk search or Dashboards

* One of the possible causes for this problem is when a user has selected a different index to collect data. Splunk by default searches inside the `main` index and all the Dashboards of the Netskope App by default use the `main` index.
* To add your custom index to the default search, navigate to `Settings -> Roles -> Select the role -> Click the indexes tab -> Search for your custom index -> Check the Default checkbox -> Save`
* To populate the Dashboards of the Netskope App from your custom index, navigate to `Netskope Add-on for Splunk -> Configuration -> Add-on Settings`. Update the `Base Event Type` with your custom index.
e.g. index=main OR index=custom_index_1 OR index=custom_index_2

### Data is not getting collected in Splunk

* Go to the Search tab. Hit the following query `index=_internal sourcetype=tanetskopeappforsplunk:log` and check the results.
* Verify the Query configured in Modular Inputs is valid and such events exist on the platform.
* Check the log file related to data collection is generated under `$SPLUNK_HOME/var/log/splunk/ta_netskopeappforsplunk_<input>.log`.
* To get the detailed logs, in the Splunk UI, navigate to Netskope Add-on For Splunk. Click on Configuration and go to the Logging tab. Select the Log level to DEBUG.
* Disable/Enable the input to recollect the data.
* Check the logs. They will be more verbose and will give the user insights into data collection.

  * Log file showing error event with "ReadTimeoutError"
      * It indicates that API is taking more time to respond than configured. Increase the value of the API Request Timeout parameter in that modular input.

### Data is missed for some specific time ranges in Alerts, Events, or Client input with Real-time data collection.

* If the data collection process gets an error even after multiple retry attempts then that specific failed time range window will be logged in the log file & data will be missed for that failed window time range.
* Check log files if any errors resulted in failed windows.
* To see all failed windows for various input types, execute the below search query.
  - ```index=_internal source="*netskope*" ERROR message=dropping_timerange | eval input=if(match(source, "netskope.log"), "Events", "Alerts") | table input, failed_window```

### Frequently data is missing for around a 1-hour time range in Alerts or Events input with Real-time data collection.

* For real-time data collection, there is a mechanism to reset data collection in case if it is lagging too much due to a high data rate.
* Please refer to the `KNOWN ISSUES` section for more details.

##### If you are still having problems, use the Command line and run this command to generate diag and send it to Netskope Splunk Support

* `$SPLUNK_HOME/bin/splunk diag --collect app:TA-NetSkopeAppForSplunk`

### If the Splunk Instance is behind a proxy, Configure Proxy settings by navigating to Netskope Add-on for Splunk -> Configuration -> Proxy

### Getting ERROR log for "Events (Iterator)" or "Alerts (Iterator)" input: 409 Concurrency conflict, retry later.

* This error occurred because the same iterator name was used by more than one Splunk instance.
* To achieve a unique name for your iterator on the server, we strongly suggest you either create/clone the input name or account name.

### Getting ERROR in Netskope checks listed under the "Health Check" section in "Monitoring Console" due to Splunk restart.

* This error is generated by a 3rd party library and cannot be controlled by us. You can ignore the errors by first disabling all inputs before restarting Splunk.

## EVENT GENERATOR

* Netskope Add-on For Splunk is provided with sample data that can be used to generate dummy data. To generate events the Eventgen app must be installed. The app and instructions can be found at https://splunkbase.splunk.com/app/1924/. This app should not be installed on a production system unless you understand the ramifications of generated data being mixed with production data.

## UNINSTALL ADD-ON

To uninstall the add-on, the user can follow the below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the TA-NetSkopeAppForSplunk folder from apps directory -> Restart Splunk

## SUPPORT

### Questions and Answers

* Access questions and answers specific to Netskope App/Add-on For Splunk at https://answers.splunk.com. Be sure to tag your question with the App.

### Support

* Support Email: support@netskope.com
* Support Offered: Email  
Support is available via email at support@netskope.com. Responses vary on working days between working hours.

## COPYRIGHT INFORMATION

Copyright (C) 2026 Netskope, Inc. All rights reserved.

## RELEASE NOTES

### Version 4.4.0
 
* Added support for Netskope Log Streaming (NLS) sourcetypes with CSV parsing.
* Added comprehensive CIM field mappings for all NLS sourcetypes to maintain compatibility with Splunk Enterprise Security.

### Version 4.3.3

* Fixed field extraction issue for Web Transactions v2.
* Added UTF-8 encoding to ensure proper handling of characters in Multi Iterator input.

### Version 4.3.2

* Added support for log streaming on Splunk Cloud TAs.

### Version 4.3.1

* Fixed data duplication issue with Connection events.

### Version 4.3.0

* Introduced a new "Events (Multi Iterator)" input option for the Application, Connection, and Network event types, enabling event collection in CSV format.
* Updated AoB to latest version (v4.5.0).

### Version 4.2.0

* Refactored checkpoint management in the Netskope iterator to simplify state handling and improve reliability.
* Enabled persistence of subscription key and subscription path in Web Transactions v2.

### Version 4.1.0

* Added Clients (Iterator) input.
* Added new Alert Types: Device and Content.
* Updated NetskopeSDK to v0.0.41.

### Version 4.0.2

* Updated Splunk SDK to v2.1.0.

### Version 4.0.1

* Fixed an issue where Web Transaction logs were not being collected due to invalid characters.

### Version 4.0.0

* Added option to include/exclude specific fields in Alerts (iterator), Events (iterator), and Web Transactions V2 inputs
* Fixed the issue of multi-threading in iterator inputs.
* Enhance internal logs to include more details.
* Add a Troubleshooting section in the TA.
* Fixed other minor issues.

### Version 3.7.3

* Updated Splunk Add-on builder version v4.2.0 to support cloud compatibility
* Added compatibility with Python 3.9.

### Version 3.7.2

* Minor Enhancements.

### Version 3.7.1

* Fixed data collection issue in Web Transactions v2

### Version 3.7.0

* Migrated AoB to latest version (v4.2.0).


### Version 3.7.0

* Migrated AoB to latest version (v4.2.0).


### Version 3.7.0

* Added support for 'Endpoint' event type in 'Events (Iterator)' input.
* Removed 'Events (Deprecated)' and 'Alerts (Deprecated)' input.
* Updated error handling logic for API response for 'Web Transaction' input.
* Added 'WebTx' postfix for 'Web Transaction V2' input user-agent.
* Upgraded Netskope SDK to 0.0.38.


### Version 3.6.0

* Added "Email Notification" feature that will send an Email if Input(s) is/are inactive for a specified duration. This feature can be enabled from the "Configuration" Page.
* Added support of proxy for "Web Transaction V2" input validation.
* Changed the default value of the "action" field to "NA" for the Connection/Page event.


### Version 3.5.0

* Added 'Netskope Quarantine File' Alert Action, to move malware alert file to the destination container and create an empty file with 'tombstone_' prefix in the source container.
* Added 'Storage Account' tab in the 'Configuration' page to configure Azure storage account details.


### Version 3.4.0

* Changed the configuration logic for the "Web Transaction V2" input to obtain the Subscription path and Subscription Key using the V2 token instead.
* Upgraded Netskope SDK to 0.0.33.
* Added backpressure mechanism for 'Web Transaction V2' input, to handle the situation of too many files in the spool location.
* Added End Datetime support for the "Events (Iterator)" and "Alerts (Iterator)" inputs.
* Added retry logic for the validation of the "Events (Iterator)" and "Alerts (Iterator)" inputs.
* Changed retry count to be configurable for the "Events (Iterator)" and "Alerts (Iterator)" inputs.
* Updated logging time to GMT/UTC timezone for all inputs.

### Version 3.3.1

* Improved the data collection logic for "Web Transaction V2" input to prevent slow ingestion during header format changes.
* Retry logic for the "Events (Iterator)" and "Alerts (Iterator)" inputs has been enhanced by adding a backoff factor between each retry call.
* Upgraded the certifi library with its latest version 2022.12.7
* Added validation for the selected events/alerts type on the "Events (Iterator)" and "Alerts (Iterator)" input page.

### Version 3.3.0

* Added the support of alert filter based on "Alert Type" for "Alerts (Iterator)" input.
* Enhanced data collection logic for "Alerts (Iterator)" input.

### Version 3.2.0

* Added support of incident data collection in "Events (Iterator)" input.
* Added CIM mapping for incident data.
* Updated thread allocation logic for iterator inputs.
* Added dynamic wait time between consecutive API calls for iterator inputs.
* Upgraded AOB to v4.1.1
* Added API rate limiting feature for iterator inputs.
* Enhanced Account token validation.

### Version 3.1.2

* Enhanced the code to avoid reconfiguring account after upgrading 3.1.2

### Version 3.1.0

* Added two new inputs "Events (Iterator)" and "Alerts (Iterator)" which collect events and alerts data using the NetSkope iterator SDK.
* Updated CIM mapping for web transaction data.
* Upgraded internal libraries.
* In the inputs page, removed the prefix "Netskope" and suffix "Input" from the input name.
* Added suffix "(Deprecated)" to the existing "Events" and "Alerts" inputs.
* Updated labels on the input page and account page for the "Web Transactions V2" input.

### Version 3.0.0

* Updated the data collection approach for Events and Alerts input.
* Updated the checkpoint format for Events, Alerts, Clients Input.
* Added support of API Token version 2 in Events, Alerts & URL List Alert Action.
* Invalid URLs handling is added in URL List Alert Action.
* Added support for multiple ingestion pipeline in Web Transaction V2 input for better performance.

### Version 2.5.1

* Upgraded AOB to v4.0.0
* Added feature to reconnect on Idle Connection Timeout in Web Transaction V2.
* Added feature to reconnect in case of any error during event processing in Web Transaction V2.

### Version 2.5.0

* Upgraded internal libraries

### Version 2.4.0

* Added new input named "Netskope Web transactions V2"

### Version 2.3.1

* Added new alert type named "UBA" in alert input.
* To avoid data loss or data duplication, Add-on will use the insertiontime instead of timestamp while fetching data from API.
* Changed the default offset parameter to zero for alert and event inputs.

### Version 2.3.0

* Fixed timestamp extraction

### Version 2.2.0

* Fixed the modular input trigger issue in case of errors.

### Version 2.1.0

* Added new Network type of event option into modular input "Netskope Events Input".
* Moved Client from a type of event option in "Netskope Events Input" to separate new modular input named "Netskope Clients Input".
* Added new configuration field named "API Request Timeout" in all modular inputs.

### Version 2.0.0

* Changed TA structure and created with Add-on builder for ease of Use
* Removed all the Data Collection part from the App and moved it to Add-on
* Fixed Web Transactions data collection issue to collect all files even though same name files in a different bucket
* Enhanced Logs for debugging purpose
* Fixed issues in Alert Actions and Moved it to Add-On
* Migrated the App & Add-on to make it Python 2 & 3 compatible.

# Binary file declaration

* cygrpc.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with GRPC module and the source code for the same can be found at https://pypi.org/project/grpc/
* cygrpc.cpython-39-x86_64-linux-gnu.so - This binary file is provided along with GRPC module and the source code for the same can be found at https://pypi.org/project/grpc/
* _yaml.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Splunk's Add-on Builder module.
* _message.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with google-cloud-pubsublite module and the source code for the same can be found at https://pypi.org/project/google-cloud-pubsublite/
* _api_implementation.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with google-cloud-pubsublite module and the source code for the same can be found at https://pypi.org/project/google-cloud-pubsublite/
* _speedups.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Splunk's Add-on Builder module and the source code for the same can be found at https://pypi.org/project/MarkupSafe/
* pvectorc.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Splunk's Add-on Builder.
* md.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Charset-Normalizer module and the source code for the same can be found at https://pypi.org/project/charset-normalizer/
* md.cpython-39-x86_64-linux-gnu.so - This binary file is provided along with the Charset-Normalizer module and the source code for the same can be found at https://pypi.org/project/charset-normalizer/
* md__mypyc.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Charset-Normalizer module and the source code for the same can be found at https://pypi.org/project/charset-normalizer/
* md__mypyc.cpython-39-x86_64-linux-gnu.so - This binary file is provided along with Charset-Normalizer module and the source code for the same can be found at https://pypi.org/project/charset-normalizer/
* _rust.abi3.so - This binary file is provided along with Cryptography module and the source code for the same can be found at https://pypi.org/project/cryptography/
* _cffi_backend.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Azure Storage Blob module and the source code for the same can be found at https://pypi.org/project/azure-storage-blob/
* _cffi_backend.cpython-39-x86_64-linux-gnu.so - This binary file is provided along with Azure Storage Blob module and the source code for the same can be found at https://pypi.org/project/azure-storage-blob/
* _message.cp310-win_amd64.pyd - This binary file is provided along with the GRPC module and the source code for the same can be found at https://pypi.org/project/protobuf/
* _api_implementation.cp310-win_amd64.pyd - This binary file is provided along with the GRPC module and the source code for the same can be found at https://pypi.org/project/protobuf/
* cygrpc.cp37-win_amd64.pyd - This binary file is provided along with GRPC module and the source code for the same can be found at https://pypi.org/project/grpc/
* cygrpc.cp39-win_amd64.pyd - This binary file is provided along with GRPC module and the source code for the same can be found at https://pypi.org/project/grpc/
* cygrpc.cp37-win32.pyd - This binary file is provided along with GRPC module and the source code for the same can be found at https://pypi.org/project/grpc/
* cygrpc.cp39-win32.pyd - This binary file is provided along with GRPC module and the source code for the same can be found at https://pypi.org/project/grpc/
* _cffi_backend.cp37-win_amd64.pyd - This binary file is provided along with Azure Storage Blob module and the source code for the same can be found at https://pypi.org/project/azure-storage-blob/
* _cffi_backend.cp39-win_amd64.pyd - This binary file is provided along with Azure Storage Blob module and the source code for the same can be found at https://pypi.org/project/azure-storage-blob/
* _rust.pyd - This binary file is provided along with Cryptography module and source code for the same can be found at https://pypi.org/project/cryptography/
* python3.dll - Dynamic Link Library (DLL) for the Python interpreter. It's part of the standard Python distribution and is automatically installed with Python.
* markupsafe - MarkupSafe implements a text object that escapes characters so it is safe to use in HTML and XML.https://pypi.org/project/MarkupSafe/