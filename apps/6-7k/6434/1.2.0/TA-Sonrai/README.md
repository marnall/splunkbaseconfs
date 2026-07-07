This is an add-on powered by the Splunk Add-on Builder.
# Sonrai Security Add-on For Splunk

## OVERVIEW
 * The Sonrai Security Add-on For Splunk pulls Tickets data from the Sonrai platform.
 * Author - Sonrai Security, Inc.

## Compatibility Matrix
* Splunk version: 9.2.x, 9.1.x and 9.0.x
* Python version: Python3
* OS Support: Linux (Centos) and Windows
* Browser Support: Chrome and Firefox

## RELEASE NOTES
### Version: 1.2.0
* Fixed token renewal issue.
* Upgraded Add-on Builder framework version to 4.2.0.

### Version: 1.1.0
* Upgraded Add-on Builder framework version to 4.1.3.

### Version: 1.0.0
* Added data collection for Tickets data.
* Added feature of workflow-actions on tickets events.

## RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk Enterprise configuration of [Search Head, Indexer and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## INSTALLATION
Sonrai Security Add-on For Splunk can be installed through UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/ folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `TA-Sonrai` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This Add-On can be set up in two ways:

* Standalone Mode: Install the Add-on app on a single machine. This single machine would serve as a `Search Head + Indexer + Heavy forwarder` for this setup.
* Distributed Environment: Install Add-on on search head and Heavy forwarder (for REST API).
    * Add-on resides on search head machine need not require any configuration here.
    * Add-on needs to be installed and configured on the Heavy forwarder system.
    + Execute the following command on Heavy forwarder to forward the collected data to the indexer. `$SPLUNK_HOME add forward-server <indexer_ip_address>:9997`
    * On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
    * Add-on needs to be installed on search head for CIM mapping

> **NOTE** : For the distributed environment, only indexes of the Forwarder would be shown in the input configuration page.

## CONFIGURATION
Configure Sonrai Security Add-on For Splunk:

### Add-on Setup
1. Configure the account from which the data needs to be collected. Detailed steps and information for Account Configuration can be found in `Account` section. Users can configure `Sonrai Account` for collecting data from Sonrai Platform:
2. Users can also configure settings corresponding to the `Proxy` or `Logging` in their respective sections.

### Account
To configure the Account and Proxy,

1. Navigate to the `Setup`-> `Configuration`.
2. Provide your Sonrai credentials and click on `Add`.

| Sonrai Account Parameters     | Mandatory or Optional | Description                                 |
| ----------------------------  | --------------------- | ------------------------------------------- |
| Account name                  | Mandatory             | Name of the account |
| Sonrai Organization ID        | Mandatory             | Endpoint Organization ID of users Sonrai account |
| Sonrai Token                  | Mandatory             | Token generated on Sonrai Portal. |
| Sonrai Host                   | Optional              | Sonrai Platform hostname to pull the events. |

### Proxy
To configure the Proxy,

1. Navigate to the `Setup`-> `Configuration`.
2. Click on the `Proxy` tab.
3. Provide your Proxy credentials and click on `Save`.

| Proxy Parameters          |   Mandatory or Optional  |                Description                                                             |
|  ----------------------   |   --------------------   |----------------------------------------------------------------------------------------|
|    Enable                 |       Optional           |  To enable or disable the proxy                                                      |
|    Proxy Type             |     Mandatory            |  Select proxy type that you want to use from the dropdown (supports HTTP/SOCK4/SOCK5)|
|    Proxy Host             |     Mandatory            |  Host or IP of the proxy server                                                        |
|    Proxy Port             |     Mandatory            |  Port for proxy server                                                                 |
|  Proxy Username           |     Optional             |  Username of the proxy server |
|  Proxy Password           |     Optional             |  Password of the proxy server |

### Logging
To configure the Logging,

1. Navigate to the `Setup`-> `Configuration`.
2. Click on the `Logging` tab.
2. Select the log level from the dropdown and click on `Save`.

### Inputs
To configure the Inputs,

1. Navigate to the `Setup`-> `Inputs`.
2. Click on `Create New Input`, window will open for configuring `Sonrai Tickets Input`.
3. Provide the required information related to input and click on `Add` to configure the input. Field descriptions are as below:

**Sonrai Tickets Input**

| Input Parameter |  Mandatory or Optional | Desciption                                                   |
| --------------- | ---------------------- | ------------------------------------------------------------ |
| Name            | Mandatory              | A name to uniquely identify the input    |
| Interval        | Mandatory              | Interval should be in range 1200 to 7200              |
| Index           | Mandatory              | Index in which the data needs to be ingested                    |
| Sonrai Account  | Mandatory              | Select Sonrai account for the given Input                 |
| Severity Category| Optional              | Select Category for which data needs to be ingested |
| Environment     | Optional               | Select environment value for which data needs to be ingested |
| Cloud Type      | Optional               | Select cloud type value for which data needs to be ingested |
| Swimlane        | Optional               | Select swimlane value for which data needs to be ingested |
| Start DateTime  | Optional               | Select UTC Start DateTime from which data needs to be fetched from sonrai portal |

> **NOTE** : If multiple inputs are created with overlapping configurations, there will be duplicate Events in Splunk.

## SEARCH
* To see ingested data for Sonrai Tickets Input, select the `Search` tab. Search ``index=* sourcetype="sonrai:sec:tickets"``.

## Workflow Actions
User can explore the ticket on Sonrai platform by using the workflow action provided, user can click on "Redirect to Sonrai Ticket" present under Event Actions.

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/TA-Sonrai.
* Remove $SPLUNK_HOME/var/log/splunk/ta_sonrai_*.log**.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance.

## TROUBLESHOOTING
### General Checks
* To troubleshoot Sonrai Security Add-on For Splunk, check $SPLUNK_HOME/var/log/splunk/ta_sonrai*.log or user can search `index="_internal" source=*ta_sonrai*.log` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_sonrai*.log ERROR` query to see ERROR logs in the Splunk UI.
* Note that all log files of this App will be generated in `$SPLUNK_HOME/var/log/splunk/` directory.

### Data Collection
* If data collection is not working then ensure that the internet is active (On a proxy machine, if proxy is enabled) and also ensure that the kvstore is enabled.
* Check `ta_sonrai_sonrai_tickets_input.log` file for Sonrai Tickets for any relevant error messages.
* If user encounters the following error `Unable to renew Sonrai token` then update the sonrai account credentials on the account configuration page.
* If creds has expired and not regerated automatically, try reconfiguring the account with the updated token.

# Binary file declaration
* _yaml.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with AoB's yaml module.
* _speedups.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with AoB's markupsafe module and the source code for the same can be found at https://pypi.org/project/MarkupSafe/

## SUPPORT
* Email: support@sonraisecurity.com 

## End User Licence Agreement:
https://eula.sonraisecurity.com/Sonrai%20Security%20Click-Through%20EUL%20Agreement.pdf

## COPYRIGHT INFORMATION

Copyright (C) Sonraí Security 2024.
