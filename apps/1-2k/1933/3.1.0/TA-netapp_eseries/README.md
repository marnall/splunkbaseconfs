# NetApp SANtricity Add-on for Splunk

# ABOUT THIS APP

* The "NetApp SANtricity Add-on for Splunk" is required in order to query the SANtricity Web Services Proxy for configuration, performance, and event data from NetApp E-Series and EF-Series storage systems.
* Author - sowings@splunk.com
* Version - 3.1.0

# COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox, Safari
* OS: Platform Independent
* Splunk Enterprise version: 8.2.x and 8.1.x
* Supported Web Services Proxy version: <=5.1
* Supported Controller Firmware version: 8.70.2, >=08.30.20.xx, 11.30.20.xx
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

# REQUIREMENTS

* `NetApp SANtricity App for Splunk` should be installed.
* Appropriate username and password for collecting data from a running instance of NetApp SANtricity Web Services Proxy.

# RELEASE NOTES

## Version 3.1.0
* Migrated NetApp SANtricity Add-on for Splunk with AOB version 4.1.0

# RECOMMENDED SYSTEM CONFIGURATION

* Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This Add-On can be set up in two ways:
    * **Standalone Mode**: Install Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup

    * **Distributed Environment**:Install Add-on on Search head and Add-on on Heavy forwarder (for REST API).

        * Add-on needs to be installed and configured on Heavy forwarder system.
        * Execute the following command on Heavy forwarder to forward the collected data to the indexer.
            * /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
        * On Indexer machine, enable event listening on port 9997 (recommended by Splunk).
        * Add-on needs to be installed on Search head for CIM mapping and search time extractions.

# INSTALLATION OF NETAPP SANTRICITY WEB SERVICES PROXY

* Download an appropriate version of NetApp SANtricity Web Services Proxy from [NetApp Support](https://mysupport.netapp.com/NOW/cgi-bin/software/?product=E-Series+SANtricity+Web+Services+%28REST+API%29&platform=Web+Services+Proxy).

* Install NetApp SANtricity Web Services Proxy according to the included installation instructions appropriate for your environment.

    * If using NetApp SANtricity Web Services Proxy 3.0+, uncheck the box to Validate storage array certificates OR manage certificates for communication between Web Services and each array outside of Splunk.

* Modify the wsconfig.xml file included with your installation.

    * Set **_env key="stats.poll.interval"_** to an appropriate interval in seconds (the suggested default is 60)

    * Set **_env key="stats.poll.save.history"_** to 1 (or greater if appropriate)

    * ONLY if using NetApp SANtricity Web Services Proxy 3.0+, set **_env key="trust.all.arrays"_** to true OR manage certificates for communication between Web Services and each array outside of Splunk

    * See more information about these settings in the appropriate User Guide at [NetApp Support](https://mysupport.netapp.com)

# INSTALLATION OF APP

* Follow the below-listed steps to install an Add-on from the bundle:
    * Download the App package.
    * From the UI navigate to Apps->Manage Apps.
    * In the top right corner select Install app from file.
    * Select Choose File and select the App package.
    * Select Upload and follow the prompts.

OR

* Directly from the Find More Apps section provided in Splunk Home Dashboard.

# CONFIGURATION OF APP

* Navigate to NetApp SANtricity Add-on, click on "Configuration" page, go to "Account" tab and then click "Add", fill in "Proxy Instance", "Web Proxy", "Username" and  "Password".

* Navigate to NetApp SANtricity Add-on, click on "Inputs" page and then click "Create New Input"->"NetApp ESeries Monitor" and fill the "Name", "Interval", "Index", "Proxy Instance" and "System ID" fields.

* Navigate to NetApp SANtricity Add-on, click on "Inputs" page and then click "Create New Input"->"NetApp ESeries Register and Monitor" and fill the "Name", "Interval", "Index", "Proxy Instance", "IP 1", "IP 2" and "Password" fields.

NOTE: By default, all connections will be done with ssl verification. To disable SSL Verification, refer [To Disable SSL Verification](#to-disable-ssl-certificate-verification).

## Upgrading Add-on from 3.0.0 to 3.1.0

* Navigate to `NetApp SANtricity Add-on for Splunk -> Inputs`. Disable all the existing inputs.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Check the upgrade option.
* Select `Upload` and follow the prompts.
* Restart Splunk if required and if prompted by Splunk.
* Navigate to the NetApp SANtricity Add-on for Splunk
* From the Inputs page, enable the already created inputs or click on "Create New Input" to create new input with required fields.

## Upgrading Add-on from 2.0.0 to Higher Version

* Due to cloud vetting check, verify ssl checkbox removed from the account configuration UI. 
* By default, Addon will verify ssl on each http connection while account configuration and data collection. To disable ssl verification, refer [To Disable SSL Verification](#to-disable-ssl-certificate-verification).
* Data Collection will not be affected for already configured accounts.


## Upgrading Add-on from 1.0.0 to 2.0.0 or Higher Version

* User is expected to run script **upgrade_from_1.0.0_to_2.0.0.py** after the app is upgraded because the changes done in the app requires this one time manual operation. User must be in bin folder of the Add-on. Command to navigate to bin folder is "**cd $SPLUNK_HOME$/etc/apps/TA-netapp_eseries/bin**". Then execute the script with following command "**$SPLUNK_HOME$/bin/splunk cmd python upgrade_from_1.0.0_to_2.0.0.py**"
* Later, user has to edit the accounts and set the passwords for them. Then user is expected to run the second script **upgrade_helper_from_1.0.0_to_2.0.0.py** with following command "**$SPLUNK_HOME$/bin/splunk cmd python upgrade_helper_from_1.0.0_to_2.0.0.py**", this will enable all those inputs for which "Proxy Instance" password had been set.
* Final step is to restart your splunk instance.

## To disable SSL Certificate Verification 

* By default, Addon will verify ssl certificate for rest communication driven through configuration available in $SPLUNK_HOME/etc/apps/TA-netapp_eseries/default/ta_netapp_eseries_account.conf.
* User can override default configuration by adding `verify_ssl = 0` parameter to the **default** stanza in $SPLUNK_HOME/etc/apps/TA-netapp_eseries/local/ta_netapp_eseries_account.conf.
* **default** stanza will hold the global parameter for each account. User also has provision to provide account specific ssl verify check by adding parameter under a **account specific** stanza in $SPLUNK_HOME/etc/apps/TA-netapp_eseries/local/ta_netapp_eseries_account.conf.
* Restart Splunk after changing configuration.

# TROUBLESHOOTING

* Environment variable SPLUNK_HOME must be set.
* To troubleshoot "NetApp ESeries Monitor" mod-input check $SPLUNK_HOME/var/log/splunk/ta_netapp_eseries_netapp_eseries.log file.
* To troubleshoot "NetApp ESeries Register and Monitor" mod-input check $SPLUNK_HOME/var/log/splunk/ta_netapp_eseries_netapp_eseries_register.log file.
* Getting Errors in data collection when only Add-on is installed.
    * Make sure that `NetApp SANtricity App for Splunk` should be installed on the same machine.

# KNOWN ISSUES
## In a distributed environment, Addon is not able to execute the saved searches created in-app:
* It will generate an Error Message like `NetApp Eseries Error: Error while executing the savedsearches.`
* It's expected because App and Addon should not be installed on the heavy forwarder and It will not cause any issues because the app will be scheduling those saved searches.

# UNINSTALL ADD-ON
To uninstall the add-on, the user can follow the below steps: SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the TA-netapp_eseries folder from apps directory -> Restart Splunk.

# BINARY FILE DECLARATION
* markupsafe - MarkupSafe implements a text object that escapes characters so it is safe to use in HTML and XML. https://pypi.org/project/MarkupSafe/

# END USER LICENSE AGREEMENT
https://gist.githubusercontent.com/anonymous/1ae065622106feee4c6b/raw/69d761818b8e0155f92c29cc7959e6d0b1b6b567/gistfile1.txt

# SUPPORT

* Support Offered: Yes [Community Supported](https://community.netapp.com/)

### Copyright (C) 2022 NetApp 
