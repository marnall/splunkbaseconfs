# DataBee App For Splunk

## OVERVIEW
* The DataBee Application for Splunk sends alerts and notable events to DataBee platform via an HTTP connector. 

## REQUIREMENTS

* Enterprise Security (To generate and send the notable events to DataBee)(https://splunkbase.splunk.com/app/263).


## COMPATIBILITY MATRIX
* Splunk version: 9.4.x, 9.3.x, 9.2.x, 9.1.x
* Python version: Python3
* OS Support: Independent
* Browser Support: Independent


## RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk Enterprise configuration of [Search Head and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## RELEASE NOTES

### Version 1.0.0

* Added the DataBee alert action to send alerts and notable events to the DataBee platform.
* Added Historical Triggered Alerts dashboard to send triggered alerts to the DataBee platform.

## INSTALLATION
DataBee App For Splunk can be installed through the UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `DataBee App For Splunk` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted.


## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This App can be set up in two ways:

1. Standalone Mode
    * Install the DataBee App For Splunk.
    * Follow all the steps mentioned in `App Setup` section to configure the App.
2. Distributed Environment
    * Install the DataBee App For Splunk on the Search Head and Heavy Forwarder.
    * Follow the steps #1 and #2 from  `App Setup` section on Heavy Forwarder.
3. Cloud Environment
    * Install the DataBee App For Splunk on Search Head.
    * Install the DataBee App For Splunk on IDM instance and configure it. (For the IDM instance Splunk support team will help) Or Setup the DataBee App For Splunk on the On-Premise Heavy Forwarder.

## CONFIGURATION
Configure DataBee App For Splunk

### App Setup
1. Configure the account from which the data needs to be sent. Detailed steps and information for Account Configuration can be found in `Account` section.
2. Users can also configure settings corresponding to the `Proxy` or `Logging` in their respective sections.


### Account
To configure the Account,

1. Navigate to the `Configuration`.
2. Provide the mentioned details as per the below table and click on `Add`.

| DataBee App Account parameters   | Mandatory or Optional | Description                                 |
| ----------------------------  | --------------------- | ------------------------------------------- |
| Account name                  | Mandatory        | Enter a unique name for this account. |
| Endpoint URL                  | Mandatory        | Enter the Endpoint URL for this account. |
| Tenant ID                     | Mandatory        | Enter the Tenant ID for this account.    |
| Datasource ID                 | Mandatory        | Enter the Datasource ID for this account.|
| API Key                       | Mandatory        | Enter the API Key for this account.      |
| Alert Actions                 | Mandatory        | Select alert actions which needs to be triggered for this account. |

### Proxy
To configure the Proxy,

1. Navigate to the `Configuration`.
2. Click on the `Proxy` tab. 
3. Provide your Proxy credential and Click on `Save`.

| Proxy Parameters          |   Mandatory or Optional  |                Description                                                             |
|  ----------------------  |   --------------------   |----------------------------------------------------------------------------------------|
|    Enable                |       Optional           |  To enable the proxy     |
|    Proxy Type            |     Optional            |  Type of the Proxy. Available options are http and socks5. Default is http.|
|    Host            |     Optional            |  Host or IP of the proxy server                                                        |
|    Port            |     Optional            |  Port for proxy server                                                                 |
|  Username          |     Optional             |  Username of the proxy server |
|  Password          |     Optional             |  Password of the proxy server |

### Logging
To configure the Logging,

1. Navigate to the `Configuration`.
2. Click on the `Logging` tab.
3. Select the log level from the dropdown and click on `Save`. By default, the log level is set to 'INFO'.


### Dashboards

1. Historical Triggered Alerts:
    * This dashboard provides details for triggered alerts.
    * Historical Triggered Alerts Panels:
        1. All the Triggered Alerts
        2. All Event Details

## Alert Actions
This application contains the following alert actions:

* **ta_databee_post_alerts_http_connector**
    * Description : To post the triggered alerts and notable events to DataBee.
    * Parameters : 
        * global_account: Select the DataBee account for which you want to post data.

## TROUBLESHOOTING
### General Checks
* To troubleshoot DataBee App For Splunk, check `$SPLUNK_HOME/var/log/Splunk/ta_databee_*.log` or user can search `index="_internal" source=*ta_databee_*.log*` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_databee_*.log* ERROR` query to see ERROR logs in the Splunk UI.
* Note that all log files of this App will be generated in `$SPLUNK_HOME/var/log/Splunk/` directory.
* App icons are not showing up: The App does not require a restart after installation for all functionalities to work. However, the icons will be visible after one Splunk restart post installation.


### Dashboards
* Panel not populating:

1. Historical Triggered Alerts:
    * If dashboard panels are not populating data, it is possible that none of the Saved Searche has triggered yet, or else according to the provided parameters of App, Severity, Alert and Triggered Time might not have any triggered alerts.

## BINARY FILE DECLARATION

* md.cpython-39-x86_64-linux-gnu.so - This binary file is provided along with Charset-Normalizer module and source code for the same can be found at https://pypi.org/project/charset-normalizer/
* md__mypyc.cpython-39-x86_64-linux-gnu.so - This binary file is provided along with Charset-Normalizer module and source code for the same can be found at https://pypi.org/project/charset-normalizer/

## SUPPORT
* Support Offered: Yes
* Support Details:
    * Email: databee_support@comcast.com

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/DataBeeAppForSplunk
* Remove $SPLUNK_HOME/var/log/Splunk/ta_databee_*.log**.
* To reflect the cleanup changes in the UI, restart the Splunk Enterprise instance.

#### ©2024 Comcast Technology Solutions