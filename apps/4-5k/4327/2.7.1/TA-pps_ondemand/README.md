# OVERVIEW

* This is an add-on powered by the Splunk Add-on Builder.
* The Proofpoint On Demand Email Security Add On fetches message and sendmail type of logs from Proofpoint server. It enriches Proofpoint data with the Common Information Model (CIM) fields and enables Proofpoint data to be easily used with Splunk Enterprise Security, Splunk App for PCI Compliance, etc.
* For dashboards with Proofpoint data, please install the Proofpoint On Demand Email Security App available at https://splunkbase.splunk.com/app/4327/ .

* Author - Proofpoint Inc
* Version - 2.7.1
* Compatible with:
  * Splunk Enterprise version: 10.0.x, 9.4.x, 9.3.x and 9.2.x
  * OS Support: Linux (CentOs, Ubuntu) and Windows
  * Browser Support: Chrome, Firefox and Safari  


# Release Notes

### Version - 2.7.1
* Introduced a checkbox to enforce checkpoint on each invocation. 
* Migrated Add-on to latest AOB version 4.5.0.

### Version - 2.7.0
* Updated data collection and checkpointing logic to handle websocket connection loss and avoid data duplication.

### Version - 2.6.0
* Added support for both KV-Service and KV-Store to enhance data collection, specifically designed to meet the needs of Splunk Cloud customers.
* Migrated Add-on to latest AOB version 4.3.0.

### Version - 2.5.1
* Updated client-websocket library.
* Minor enhancements.

### Version - 2.5.0
* Updated the checkpoint logic.

### Version - 2.4.0
* Migrated Add-on to AOB version 4.1.4.

### Version - 2.3.0
* Added data collection and CIM mapping support for Audit data.
* Enhanced extractions for recipient_domain field.

### Version - 2.2.3
* Fixed issue related to Splunk Cloud Compatibility.

### Version - 2.2.0
* Migrated Proofpoint On Demand Email Security Add-on with AOB version 4.1.0

### Version - 2.1.0
* Improved CIM mappings.
* Added 300 as the default value of "Retry Interval"
* Improved the logic of data collection to reduce gaps in data

### Version - 2.0.0
* Added Support for Splunk 8 and Made add-on Python2 and Python3 compatible. 
* Improved CIM mappings.

### Version - 1.0.3
* Changed the index time to use actual logged time of an event.

### Version - 1.0.2
* Added support for Splunk running on IPv6 host.

### Version - 1.0.1
* Fixed issue while adding account with proxy enabled.


# OPEN SOURCE COMPONENTS AND LICENSES

* Proofpoint On Demand Email Security Add On uses websocket-client library which is licensed under free or open source licenses. We wish to thank the contributors to this project.

    websocket-client version 0.57.0 https://pypi.org/project/websocket-client/ (LICENSE https://github.com/websocket-client/websocket-client/blob/master/LICENSE)

# RECOMMENDED SYSTEM CONFIGURATION

* Because this Add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This Add-On can be set up in two ways:

1. Standalone Mode: Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.
2. Distributed Environment: Install Add-on on search head and Heavy forwarder.
    * Add-on resides on search head machine need not require any configuration here.
    * Add-on needs to be installed and configured on the Heavy forwarder system.
    * Execute the following command on Heavy forwarder to forward the collected data to the indexer.
      /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
    * On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
    * If you are using custom index define it on the indexer.
    * Add-on needs to be installed on search head for CIM mapping.

# INSTALLATION OF APP
Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps-> Manage Apps`.
* In the top right corner select `Install the app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

OR

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## CONFIGURATION
## 1. Add Proofpoint Credentials
 On Splunk instance, navigate to Proofpoint on demand email security Add-on for Splunk, click on `Configuration -> Account` tab and fill in the details asked, and click "Save". Field descriptions are as below:

| Field Name           | Field Description                              |
| -------------------  | -----------------------------------------------|
|  Account Profile\*   | Unique name to identify the account            |
|  Cluster ID\*        | Cluster ID                                     |
|  API Key\*           | API Key                                        |

**Note**: `*` denotes required fields

## 2. Configure Proxy (Optional)
Navigate to `Proofpoint on demand email security Add-on for Splunk -> Configuration -> Proxy` tab, fill in the details asked and click "Save". Field descriptions are as below:

| Field Name          | Field Description                                                              |
| ------------------- | ------------------------------------------------------------------------------ |
| Enable              | Enable/Disable proxy                                                           |
| Proxy Type\*        | Type of proxy                                                                  |
| Host\*              | Hostname/IP Address of the proxy                                               |
| Port\*              | Port of proxy                                                                  |
| Username            | Username for proxy authentication (Username and Password are inclusive fields) |
| Password            | Password for proxy authentication (Username and Password are inclusive fields) |

**Note**: `*` denotes required fields when Enable checkbox is selected.

## 3. Configure Logging (Optional)
Navigate to `Proofpoint on demand email security Add-on for Splunk -> Configuration -> Logging` tab, select the prefered "Log level" value from the dropdown and click "Save".

## 4. Configure Data Inputs
* Navigate to the `Proofpoint on demand email security Add-on for Splunk -> Inputs` page.
* Click on `Create New Input`, one dropdown will be open with options:
    * `Proofpoint Mail Log`
    * `Proofpoint Message Log`
    * `Proofpoint Audit Log`
* Select an option and a form will open accordingly.
* Fill in the details asked in the pop-up form and click on `Add` to start the data collection.
* Field descriptions are as below:

| Field Name           | Field Description                                             |
| -------------------  | --------------------------------------------------------------|
|  Name\*              | Unique name for the data input                                |
|  Retry Interval\*    | Retry interval in seconds (default: 300,Valid range:60 to 300)|
|  Index\*             | Index in which data will be collected (default: main index)   |
|  Account Profile\*   | Select account profile configured under Account tab           |

**Note**:- User with Splunk admin role can configure and access the add-on configuration. If user is not able to view the add-on configuration page then please provide the admin role to the user from Settings -> Access controls -> Users -> Select a User -> Provide admin role -> Save.

# UPGRADE

### General upgrade steps:
* Log in to Splunk Web and navigate to `Apps > Manage Apps`.
* Click `Install app from file`.
* Click `Choose file` and select the Proofpoint on demand email security Add-on installation file.
* Check the `Upgrade` checkbox.
* Click on `Upload`.
* Restart Splunk.

### Upgrade from version 2.7.0 to version 2.7.1
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security Add-on from version 2.7.0 to version 2.7.1.

### Upgrade from version 2.6.0 to version 2.7.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security Add-on from version 2.6.0 to version 2.7.0.

### Upgrade from version 2.5.1 to version 2.6.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security Add-on from version 2.5.1 to version 2.6.0.

### Upgrade from version 2.5.0 to version 2.5.1
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security Add-on from version 2.5.0 to version 2.5.1.

### Upgrade from version 2.4.0 to version 2.5.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security Add-on from version 2.4.0 to version 2.5.0.

### Upgrade from version 2.3.0 to version 2.4.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security Add-on from version 2.3.0 to version 2.4.0.

### Upgrade from version 2.2.3 to version 2.3.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security Add-on from version 2.2.3 to version 2.3.0.

### Upgrade from version 2.1.0 to version 2.2.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security Add-on from version 2.1.0 to version 2.2.0.

### Upgrade to version 2.1.0
* Follow the `General upgrade steps` section.
* No additional steps are required to upgrade Proofpoint On Demand Email Security Add-on to version 2.1.0.

# TROUBLESHOOTING

* Check below log files.
    * `$SPLUNK_HOME/var/log/splunk/splunkd.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_pps_ondemand_proofpoint_message_log.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_pps_ondemand_proofpoint_mail_log.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_pps_ondemand_proofpoint_audit_log.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_pps_ondemand_account_validation.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_pps_ondemand_rh_message.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_pps_ondemand_rh_mail.log`
* User can search for ERROR logs in the Splunk using following query.
    * `index="_internal" source=*ta_pps_ondemand*.log ERROR`
    * `index="_internal" sourcetype=tappsondemand:log ERROR`
* Check that you have selected the correct sourcetype.
* Make sure that API Key which you have entered while configuring the Account has not expired.
* Make sure that Splunk restarts or disabling of input action should not be performed while input (data collection) is running.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/TA-pps_ondemand
* Remove $SPLUNK_HOME/var/log/splunk/**ta_pps_ondemand_proofpoint_mail_log.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_pps_ondemand_proofpoint_message_log.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_pps_ondemand_proofpoint_audit_log.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_pps_ondemand_account_validation.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_pps_ondemand_rh_message.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_pps_ondemand_rh_mail.log**
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# SUPPORT

* Access questions and answers specific to Proofpoint On Demand Email Security Add On at https://answers.splunk.com.
* Support Offered: Yes
* Support Email: 
* Please visit https://answers.splunk.com, and ask your question regarding Proofpoint On Demand Email Security Add On. Please tag your question with the correct App Tag, and your question will be attended to.

**Copyright (c) 2025 by Proofpoint, Inc.  All Rights Reserved.**