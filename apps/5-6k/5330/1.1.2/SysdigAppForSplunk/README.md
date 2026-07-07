# Sysdig App for Splunk

## OVERVIEW
* The App delivers a user experience designed to make Splunk immediately useful and relevant for typical tasks and roles. The Sysdig App for Splunk will provide the below functionalities:  
  * Dashboards to visualize the Sysdig data.
  * The App uses data collected by the Sysdig Add-on to present the dashboards.

* Author - Sysdig, Inc 
* Version - 1.1.2
* Prerequisites - Sysdig Add-on for Splunk
* Splunk version: 9.0.x, 8.2.x and 8.1.x
* OS Support: Platform independent
* Browser Support: Chrome and Firefox

## END USER LICENSE AGREEMENT
https://sysdig.com/license-agreement/

## RELEASE NOTES

### Version: 1.1.2
* Added support of SysdigSecureEvents (which contains runtime policy events) sourcetype for Policy Events Overview dashboard.

### Version: 1.1.1
* Added support of runtime policy events for Policy Events Overview dashboard.

### Version: 1.1.0
* Bundled JQuery v3.6.0 within app package.
* Bundled underscore.js v1.6.0 in the app package.
* Updated codebase to adhere to appinspect best practices and to support latest Splunk version.

### Version: 1.0.1
* Update Simple XML dashboards version.

### Version: 1.0.0
* Initial release

## RECOMMENDED SYSTEM CONFIGURATION
* As this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This App  can be set up in two ways:

1. Standalone Mode:  Install App on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup  
2. Distributed Environment: Install App on the search head.

* App resides on the search head machine to visualize the data coming from forwarders.

# INSTALLATION #
* Follow the below-listed steps to install an Add-on from the bundle:
    * Install the App bundle by:
    * Download the App package.
    * In the UI navigate to: `Apps->Manage Apps`.
    * In the top right corner select `Install app from file`.
    * Select `Choose File` and select the App package.
    * Select `Upload` and follow the prompts.

## UPGRADE TO V1.1.2 FROM V1.1.1
* Follow the steps mentioned below in order to upgrade the App:
    * Go to Apps > Manage Apps and click on the "Install app from file".
    * Click on "Choose File" and select the SysdigAppForSplunk installation file.
    * Check the Upgrade app checkbox and click on Upload.
    * Restart the Splunk if prompted.
    * Bump (<Hostname: port>/<language>/_bump) the dashboards once.
        * Ex.: http://localhost:8000/en-US/_bump

## UPGRADE TO V1.1.1 FROM V1.1.0
* Follow the steps mentioned below in order to upgrade the App:
    * Go to Apps > Manage Apps and click on the "Install app from file".
    * Click on "Choose File" and select the SysdigAppForSplunk installation file.
    * Check the Upgrade app checkbox and click on Upload.
    * Restart the Splunk if prompted.
    * Bump (<Hostname: port>/<language>/_bump) the dashboards once.
        * Ex.: http://localhost:8000/en-US/_bump

## UPGRADE TO V1.1.0 FROM V1.0.1
* Follow the steps mentioned below in order to upgrade the App:
    * Go to Apps > Manage Apps and click on the "Install app from file".
    * Click on "Choose File" and select the SysdigAppForSplunk installation file.
    * Check the Upgrade app checkbox and click on Upload.
    * Restart the Splunk if prompted.
    * Bump (<Hostname: port>/<language>/_bump) the dashboards once.
        * Ex.: http://localhost:8000/en-US/_bump


## DASHBOARDS
1. Policy Events Overview
2. Activity Audit Overview
3. Audit Tap Overview

## CONFIGURATION
* Configure Macro:
    * If the data is collected in default index, then no need to perform this step. But if the data is collected in any other index, then do the below steps.
        * Go to Settings->Advanced search->Search macros
        * Select "Sysdig App for Splunk" in App context
        * Select the macro `sysdig_app_index`
        * Modify the index value to specify the index in which the data is collected
   
## DATA MODEL CONFIGURATION
* The Data Model used in this application is not accelerated. Admin should manually accelerate the Data Model.
* The Data Model used in this application should be accelerated to achieve better performance in loading dashboard panels. 
* Admin can enable/disable acceleration or change the acceleration period by the following steps:
    1. On Splunk's menu bar, Click on Settings -> Data models.
    2. From the list for Data models, Search for "Sysdig" data model, click "Edit" in the "Action" column of the row for the Data model for which acceleration needs to be enabled or disabled.
    3. From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
    4. Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    5. If acceleration is enabled, select the summary range to specify the acceleration period.
    6. To save acceleration changes click on the Save button.

* Warning: Acceleration may increase storage and processing costs.

## REBUILDING DATA MODEL
* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:
    1. On Splunk's menu bar, Click on Settings -> Data models.
    2. From the list for Data models, expand the row by clicking ">" arrow in the first column of the row for the Data model "Sysdig" for which acceleration needs to be rebuilt. This will display an extra Data Model information in "Acceleration" section.
    3. From the "Acceleration" section click on "Rebuild" link.
    4. Monitor the status of "Rebuild" in the field "Status" of "Acceleration" section. Reload the page to get the latest rebuild status.

## TROUBLESHOOTING

### Dashboard not populating
* After you complete the installation of the App, all the dashboards start populating data. If you don’t see data in the dashboards, use the following steps for troubleshooting:
    * Please verify that the index specified in the macro `sysdig_app_index` is the same in which data is collected
    * Please verify the data collection by hitting below search:
        * `` `sysdig_app_index ` ``

## UNINSTALL APP
* To uninstall app, user can follow below steps:
    * SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the SysdigAppForSplunk folder from apps directory 
    * Restart Splunk

## SUPPORT
* Support : https://sysdig.com/support/
* Support Offered : Support Ticket
* Support is offered via a mechanism of support tickets.

## COPYRIGHT INFORMATION
Copyright 2022 Sysdig, Inc. All Rights Reserved.