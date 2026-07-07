# Sysdig Add-on for Splunk

## OVERVIEW
* Categorize the data which is forwarded from Sysdig via HTTP Event Collector (HEC) in different sourcetypes
* Parse the data and extract important fields
* Author - Sysdig, Inc 
* Version - 1.1.2
* Splunk version: 9.0.x, 8.2.x and 8.1.x
* OS Support: Platform independent
* Browser Support: Chrome and Firefox
* Common Information Model: >=4.17.0 and <=5.0.1

## END USER LICENSE AGREEMENT
https://sysdig.com/license-agreement/

## RELEASE NOTES

### Version: 1.1.2
* Added support of SysdigSecureEvents sourcetype (which contains runtime policy events).

### Version: 1.1.1
* Added support of runtime policy events.

### Version: 1.1.0
* Updated codebase to adhere to appinspect best practices and to support latest Splunk version.
* Updated field mapping to support CIM v5.0.1.

### Version: 1.0.0
* Initial release

## RECOMMENDED SYSTEM CONFIGURATION
* As this Add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This Add-on  can be set up in two ways:

1. Standalone Mode: Install Add-on on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup  
2. Distributed Environment: Install Add-on on search head and Heavy forwarder
    * Add-on resides on search head machine does not require any configuration here.
    * Add-on needs to be installed and configured on the Heavy forwarder system.
    * Configure an HTTP Event Collector on Heavy Forwarder and use the token generated here to forward data from Sysdig platform
    * Execute the following command on Heavy forwarder to forward the collected data to the indexer. /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
    * On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
    * Add-on needs to be installed on search head for CIM mapping and Custom Data model created in the app.

## INSTALLATION
* Follow the below-listed steps to install an Add-on from the bundle:
    * Download the Add-on package.
    * In the UI navigate to: `Apps->Manage Apps`.
    * In the top right corner select `Install app from file`.
    * Select `Choose File` and select the Add-on package.
    * Select `Upload` and follow the prompts.

## UPGRADE TO V1.1.2 FROM V1.1.1
* Follow the steps mentioned below in order to upgrade the Add-On:
    * Go to Apps > Manage Apps and click on the "Install app from file".
    * Click on "Choose File" and select the TA-Sysdig installation file.
    * Check the Upgrade app checkbox and click on Upload.
    * Restart the Splunk if prompted.

## UPGRADE TO V1.1.1 FROM V1.1.0
* Follow the steps mentioned below in order to upgrade the Add-On:
    * Go to Apps > Manage Apps and click on the "Install app from file".
    * Click on "Choose File" and select the TA-Sysdig installation file.
    * Check the Upgrade app checkbox and click on Upload.
    * Restart the Splunk if prompted.

## UPGRADE TO V1.1.0 FROM V1.0.0
* Follow the steps mentioned below in order to upgrade the Add-On:
    * Go to Apps > Manage Apps and click on the "Install app from file".
    * Click on "Choose File" and select the TA-Sysdig installation file.
    * Check the Upgrade app checkbox and click on Upload.
    * Restart the Splunk if prompted.


## CONFIGURATION
* Enable HTTP Event Collector(HEC) and create an HEC token on the forwarder as per the documentation here:https://docs.splunk.com/Documentation/Splunk/8.1.0/Data/UsetheHTTPEventCollector
* Follow document:https://docs.sysdig.com/en/forwarding-to-splunk.html
 to configure the Sysdig platform to forward data to splunk.

## TROUBLESHOOTING

### Data is not getting collected in splunk.
* Ensure that the HTTP Event Collector(HEC) is enabled

## EVENT GENERATOR
Sysdig Add-on For Splunk is provided with sample data that can be used to generate dummy data. To generate events the Eventgen app must be installed. The app and instructions can be found at https://splunkbase.splunk.com/app/1924/. This app should not be installed on a production system unless you understand the ramifications of generated data being mixed with production data.

## UNINSTALL ADD-ON
* To uninstall add-on, user can follow below steps: 
    * SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the TA-Sysdig folder from apps directory 
    * Restart Splunk

## SUPPORT
* Support : https://sysdig.com/support/
* Support Offered : Support Ticket
* Support is offered via a mechanism of support tickets.

## COPYRIGHT INFORMATION
Copyright 2022 Sysdig, Inc. All Rights Reserved.
