# Team Cymru Feed App For Splunk
## OVERVIEW
The Team Cymru Feed App For Splunk pulls Indicators from the API Feed platform. The integration provides dashboards for visualization.


## COMPATIBILITY MATRIX
* Splunk version: 10.3.x, 10.2.x, 10.1.x, 10.0.x, 9.4.x, 9.3.x, 9.2.x
* Python version: Python3
* OS Support: Independent
* Browser Support: Independent


## RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk Enterprise configuration of [Search Head, Indexer and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## RELEASE NOTES


### Version 1.0.1

* Added `python.required = 3.9` to Python-backed stanzas for Splunk Cloud Platform compatibility (Splunk 10.2 / AppInspect 4.1+).
* Updated Splunk compatibility range: added 10.0.x, 10.1.x, 10.2.x, 10.3.x; dropped 9.1.x (Python 3.9 not available).
* Upgraded bundled Splunk SDK for Python to 2.1.1.

### Version 1.0.0

* Added data collection for Team Cymru Feed API.
* Added IP Overview Dashboard.

## INSTALLATION
Team Cymru Feed App For Splunk can be installed through UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `Team Cymru Feed App For Splunk App` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This App can be set up in two ways:

1. Standalone Mode
    * Install the Team Cymru Feed App For Splunk App.
    * Follow all the steps mentioned in `App Setup` section to configure the App.
2. Distributed Environment
    * Install the Team Cymru Feed App For Splunk App on the Search Head and Heavy Forwarder.
    * Follow the steps #1, #2 , #3 and #4 from  `App Setup` section on Heavy Forwarder.
    * Follow the step #5 from  `App Setup` section on Search Head.
    * In case of Search Head Clustering, make sure that steps #4 and #5 from `App Setup` are configured only on single search head. In such cases, the configuration will not be visible on other search heads. This is recommended approach.
    * Follow the step #5 from `App Setup` section on Search Head. Following these steps will replicate the configuration on all search heads.
3. Cloud Environment
    * Install the Team Cymru Feed App For Splunk on Searchhead.
    * Install the Team Cymru Feed App For Splunk on IDM instance and configure it. (For the IDM instance Splunk support team will help) Or Setup the Team Cymru Feed App For Splunk on the On-Premise Heavy Forwarder.

## CONFIGURATION
Configure Team Cymru Feed App For Splunk

### App Setup
1. Configure the account from which the data needs to be collected. Detailed steps and information for Account Configuration can be found in `Account` section.
2. Users can also configure settings corresponding to the `Proxy` or `Logging` in their respective sections.

> **NOTE** :  There might be some delay for the dashboards to populate, as these dashboards are based on savedsearches.

### Account
To configure the Account,

1. Navigate to the `Configuration`.
2. Provide your Team Cymru Feed App Platform address, credentials and click on `Add`.

| Team Cymru Feed App Account parameters   | Mandatory or Optional | Description                           |
| ---------------------------------------- | --------------------- | ------------------------------------- |
| Account name                             | Mandatory             | Enter a unique name for this account. |
| Username                                 | Mandatory             | Enter the username for this account.  |
| Password                                 | Mandatory             | Enter the password for this account.  |

### Proxy
To configure the Proxy,

1. Navigate to the `Configuration`.
2. Click on the `Proxy` tab. 
3. Provide your Proxy credential and Click on `Save`.

| Proxy Parameters          |   Mandatory or Optional  |                Description                                                             |
|  ----------------------  |   --------------------   |----------------------------------------------------------------------------------------|
|    Enable                |       Optional           |  To enable the proxy     |
|    Proxy Type            |     Required            |  Type of the Proxy. Available options are http and socks5. Default is http.|
|    Host            |     Required            |  Host or IP of the proxy server                                                        |
|    Port            |     Required            |  Port for proxy server                                                                 |
|  Username          |     Optional             |  Username of the proxy server |
|  Password          |     Optional             |  Password of the proxy server |

### Logging
To configure the Logging,

1. Navigate to the `Configuration`.
2. Click on the `Logging` tab.
3. Select the log level from the dropdown and click on `Save`. By default the log level is set to 'INFO'.


### Inputs
To configure the Inputs,

1. Navigate to the `Inputs`.
2. Click on `Create New Input` and Select the "Team Cymru Feed Indicator" or "Team Cymru Feed API".
3. Provide the required information related to input and click on `Add` to configure the input.

* Parameter of Team Cymru feed API
| Input Parameter |  Mandatory or Optional | Description                                                  |
| --------------- | ---------------------- | ------------------------------------------------------------ |
| Name            | Mandatory              | A name to uniquely identify the input                        |
| Interval        | Mandatory              | Time interval of input in seconds. Default=86400               |
| Index           | Mandatory              | Select the index in which data should be collected. Only required if "Collection Type" is set to "Index".       |
| Team Cymru Feed API Account| Mandatory      | Select the Team Cymru Feed API Account for which you want to collect data.             |
| API Type        | Mandatory              | Select the API Type to collect data of that API Type |


## TROUBLESHOOTING
### General Checks
* To troubleshoot Team Cymru Feed App For Splunk, check `$SPLUNK_HOME/var/log/Splunk/ta_team_cymru_feed*.log` or user can search `index="_internal" source=*ta_team_cymru_feed_*.log*` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_team_cymru_feed*.log* ERROR` query to see ERROR logs in the Splunk UI.
* Note that all log files of this App will be generated in `$SPLUNK_HOME/var/log/Splunk/` directory.
* App icons are not showing up: The App does not require restart after the installation in order for all functionalities to work. However, the icons will be visible after one Splunk restart post installation.


### Data Collection
* If data collection is not working then ensure that the internet is active (On a proxy machine, if proxy is enabled) and also ensure that the kvstore is enabled.
* Check `ta_team_cymru_feed*.log*` file for  Team Cymru Feed App For Splunk data collection for any relevant error messages.
* Note: If users edit input data during the collection process, there may be a possibility of some duplication of data.

### Dashboards
* Panel not populating:

    1. IP Overview Dashboard:
        * IP Overview Dashboard Panels:
            1. IPs Detail
        * Please ensure that the collected data is in the index as mentioned in the `team_cymru_api_index` Macro.
        * Note: To use `Create Alert` feature a user must be logged in with admin credentials.

## BINARY FILE DECLARATION

* md.cpython-39-x86_64-linux-gnu.so - This binary file is provided along with Charset-Normalizer module and source code for the same can be found at https://pypi.org/project/charset-normalizer/
* md__mypyc.cpython-39-x86_64-linux-gnu.so - This binary file is provided along with Charset-Normalizer module and source code for the same can be found at https://pypi.org/project/charset-normalizer/

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/TeamCymruFeedAppForSplunk
* Remove $SPLUNK_HOME/var/log/Splunk/ta_team_cymru_feed*.log**.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## SUPPORT
* Support Offered: Yes
* Support Details:
    * Email: support@cymru.com

#### Copyright © Pure Signal Feed ™ 2007-2025. All rights reserved.
