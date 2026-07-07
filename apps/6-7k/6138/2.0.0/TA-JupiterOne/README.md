## JupiterOne Add-on for Splunk

## OVERVIEW

* The Add-on typically imports and enriches data from JupiterOne platform, creating a rich data set ready for direct analysis or use in an App. The JupiterOne Add-on for Splunk will provide the below functionalities:
    * Collects data from the REST endpoint of the JupiterOne platform.
    * Parse the data and extract important fields.

* Author - JupiterOne, Inc.
* Version - 2.0.0

## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox
* OS: Platform Independent
* Splunk Enterprise version: 8.0.X, 8.1.X, 8.2.X
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

## RELEASE NOTES
### Version 2.0.0
* Major version update with enhanced features and improvements.

### Version 1.5.0
* Compatibility Updates.

### Version 1.4.0
* Added ability to specify the base URL used to communicate with JupiterOne.

### Version 1.3.0
* Added Custom Command (jupiteronesearch) to search the query on JupiterOne Platform and display the response in Splunk.

### Version 1.2.0
* Added workflow action to search field value of the entities on the JupiterOne platform.
* Updated the TA logo.

### Version 1.1.0
* Added checkbox on inputs page to indicate whether to collect alert related entities or not.
* Added data collection logic to collect entities associated with the alert.
* Added workflow action to explore more details of alert-related entities on the JupiterOne platform.

### Version 1.0.0
* Added support for data collection of JupiterOne Alerts.
* Added correlation search to create notable events of JupiterOne Alerts.

## RECOMMENDED SYSTEM CONFIGURATION
* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This Add-On can be set up in two ways:

1) Standalone Mode: Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy Forwarder for this setup.  
2) Distributed Environment: Install Add-on on Search Head and Heavy Forwarder (for REST API).

* Add-on resides on Search Head machine need not require any configuration here.
* Add-on needs to be installed and configured on the Heavy Forwarder system.
* Execute the following command on Heavy Forwarder to forward the collected data to the indexer.
  `/opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997`
* On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
* Add-on needs to be installed on Search Head for CIM mapping.

## INSTALLATION
Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps-> Manage Apps`.
* In the top right corner select `Install the app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## CONFIGURATION
## 1. Add JupiterOne Credentials
To generate the JupiterOne API key, open JupiterOne platform and navigate to `Settings -> Users & Access` page. Thereafter click on `API Keys` to generate new key. Thereafter, click on `NEW API KEY` button and enter "Key name and Days before expiration". Thereafter click on `CREATE` button. Thereafter on Splunk instance, navigate to JupiterOne Add-on for Splunk, click on `Configuration -> JupiterOne Account tab` and click on `Add`, fill in the details asked and click "Save". Field descriptions are as below:

| Field Name           | Field Description                 |
| -------------------  | --------------------------------- |
| Account Name\*       | Unique name for account           |
| Account Id\*         | JupiterOne account Id             |
| API Key\*            | JupiterOne API key                |

**Note**: `*` denotes required fields

## 2. Configure Proxy (Optional)
Navigate to `JupiterOne Add-on for Splunk -> Configuration -> Proxy` tab, fill in the details asked and click "Save". Field descriptions are as below:

| Field Name          | Field Description                                                              |
| ------------------- | ------------------------------------------------------------------------------ |
| Enable              | Enable/Disable proxy                                                           |
| Proxy Type\*        | Type of proxy                                                                  |
| Host\*              | Hostname/IP Address of the proxy                                               |
| Port\*              | Port of proxy                                                                  |
| Username            | Username for proxy authentication (Username and Password are inclusive fields) |
| Password            | Password for proxy authentication (Username and Password are inclusive fields) |

**Note**: `*` denotes required fields

## 3. Configure Logging (Optional)
Navigate to `JupiterOne Add-on for Splunk -> Configuration -> Logging` tab, select the prefered "Log level" value from the dropdown and click "Save".

## 4. Create Data Input
Navigate to `JupiterOne Add-on for Splunk -> Inputs`. Click on "Create New Input". Fill in the details asked and click "Add". Field descriptions are as below:

**JupiterOne Alerts Input**

| Field Name           | Field Description                                                               |
| -------------------  | ------------------------------------------------------------------------------- |
| Name\*               | Unique name for the data input                                                  |
| Interval\*           | Time interval of input in seconds                                               |
| Index\*              | Index where data will be stored                                                 |
| JupiterOne Account\* | Account that you have configured in "Configuration" tab                         |
| Pull Alert Related Objects | Checkbox to pull alert related objects or not                             |    
| Start Date           | Date in UTC from when to start collecting data. Default will be last 30 days  |

**Note**: `*` denotes required fields

## 5. Configure number of threads (Optional)
* After upgradation from v1.0.0 to 1.1.0 or any higher version, If a user wants to configure the number of threads to collect alert-related entities then follow the below steps otherwise it will be half of the CPU count.
    * Place the stanza at $SPLUNK_HOME/etc/apps/TA-JupiterOne/local/ta_jupiterone_settings.conf as mentioned below:
      ```
      [threads]
      no_of_threads = <Specify the no. of threads to collect alert related entities>
      ```

## UPGRADE

### From v1.0.0 to v1.X.X

#### Follow the below steps to upgrade the Add-on
* Disable all the inputs from the Inputs page of JupiterOne Add-on for Splunk.
* Install the JupiterOne Add-on for Splunk.
* Restart the Splunk if required and if prompted by Splunk.
* Navigate to the JupiterOne Add-on for Splunk.
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.
* NOTE: For Running Custom command except Account Configuration no additional configurations are required.

## Correlation SavedSearch
* "Threat - JupiterOne Alerts - Rule" : This savedsearch is used to create notable events.
* Note: If you want to add custom field on incident review, then visit the following link :
[Adding custom field on incident review page](https://www.splunk.com/en_us/blog/security/modifying-the-incident-review-page.html)

## WorkFlow Actions
### JupiterOne: Explore Entity on J1 Portal

* The app provides a workflow action "JupiterOne: Explore Entity on J1 Portal" for event type "jupiterone_alert_entities" to explore details about a specific entity on JupiterOne Platform.

### JupiterOne: Search Field on J1 Portal

* The app provides a workflow action "JupiterOne: Search Field on J1 Portal" for any event type to search field values of the entities on JupiterOne Platform.

**NOTE:** If the user wants to use host value other than "apps.us.jupiterone.io" then user needs to manually configure the workflow action as mentioned below:

* Go to settings > Fields > Workflow actions.
* In App filter select the "JupiterOne Add-on for Splunk" and select the "JupiterOne: Search Field on J1 Portal" workflow action.
* In the "URI" field, replace the "apps.us.jupiterone.io" with the host of the JupiterOne portal.
* Click on the save button.

## CUSTOM COMMANDS
* This application contains following custom commands
    * jupiteronesearch - This command provides response of the query which you have passed in query parameter via REST API call to JupiterOne and displays the response in Splunk.
        * Parameters :
            * query (required) - A query that user wants to search.
            * account_name (required) - Account name which is configured in Configuration tab of JupiterOne Add-on. User has to configure the account first before using this command.
    * NOTE : Non-admin Users can not run the custom command.

## TROUBLESHOOTING
### If Data is not getting collected in Splunk
* Check `$SPLUNK_HOME/var/log/splunk/splunkd.log` and `$SPLUNK_HOME/var/log/splunk/ta_jupiterone_*.log` log files.
* Check that you have selected correct sourcetype.
* Make sure that API Key which you have entered while configuring Account is not expired.
* Make sure that splunk restart or disabling of input action should not be performed while input (data collection) is running.

### If Data is not getting collected in Splunk when you run the custom command.
* Check `$SPLUNK_HOME/var/log/splunk/splunkd.log` and `$SPLUNK_HOME/var/log/splunk/jupiteronesearch.log` log files.
* Make sure that API Key which you have entered while configuring Account is not expired.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

### If not able to collect alert related entities for existing inputs after upgradation from V1.0.0 to V1.1.0 or any higher version
* The user needs to create new input or clone that input by checking the "Pull Alert Related Objects" checkbox.

## UNINSTALL ADD-ON
To uninstall the add-on, the user can follow the below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the TA-JupiterOne folder from apps directory -> Restart Splunk.

## END USER LICENSE AGREEMENT
https://jupiterone.com/terms/

## SUPPORT
* Support Offered: Yes
* Email: <support@jupiterone.com>

## BINARY FILE DECLARATION
* markupsafe - MarkupSafe implements a text object that escapes characters so it is safe to use in HTML and XML. https://pypi.org/project/MarkupSafe/

### Copyright 2021 JupiterOne, Inc.
