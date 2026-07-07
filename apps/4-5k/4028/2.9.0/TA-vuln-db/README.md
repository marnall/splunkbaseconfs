ABOUT THIS APP
-----------------------------------------------------------------------------
* This is an add-on powered by the Splunk Add-on Builder.
* The VulnDB Splunk Add-on is designed to communicate with the VulnDB database of vulnerability information, accessible via REST API.
* This application requires an active subscription to the VulnDB REST API.

* Prior to installation, be sure to have the TA-vuln-db.tgz or TA-vuln-db.spl file on your local machine (Web Interface installation) or on the target Splunk server(s) (Shell installation), where it is readily available for the installation process.

* Author - Flashpoint
* Version - 2.9.0
* Creates Index - False
* Compatible with:
   * Splunk Enterprise version: 10.0.x, 9.4.x, 9.3.x and 9.2.x
   * OS: Platform independent
* This application is a VulnDB Flashpoint Add-on for Splunk(TA-vuln-db).

# Requirements
* You need Consumer Key and Consumer Secret to collect vulnerabilities from the VulnDB. 

Installation - Web Interface:
-------------------------------------------------------------------------------
* Log into Splunk with an administrator account.
* Click on the gear icon for Application Management.
* Click on the "Install app from file button".
* Click the "Choose File" button and browse to the location on your local machine
* where the TA-vuln-db.tgz or TA-vuln-db.spl file is located and select it.
* Click the "Upload button".

Installation - Shell:
-------------------------------------------------------------------------------
* Log into the shell for your Splunk server
* Change to the Splunk application folder: 
* cd $SPLUNK_HOME/etc/apps
* Extract the application from the archive file: 
   * tar xzf <archive location>.
* Verify that the app has the proper permissions for the OS:
   * chown -R splunk:splunk $SPLUNK_HOME/etc/apps/TA-vuln-db.
   * Restart Splunk.
   * $SPLUNK_HOME/bin/splunk restart.

UPGRADE:
-------------------------------------------------------------------------------

Follow the below steps to upgrade the App.

* Go to Apps > Manage Apps and click on the "Install app from file". 
* Click on "Choose File" and select the TA-vuln-db installation file. 
* Check the Upgrade app checkbox and click on Upload. 
* Restart the Splunk instance.

**Note** :  Before upgrade disable all the enabled inputs from the UI Inputs Page. Once the upgrade is successful, user can re-enable the inputs from the UI Inputs Page.

TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
-------------------------------------------------------------------------------

This Add-On can be set up in two ways:

* Standalone Mode: 
      - Install the Add-on app on a single machine. 
      - This single machine would serve as a Search Head + Indexer + Heavy Forwarder for this setup.
* Distributed Environment: 
      - Install Add-on on Search Head and Heavy Forwarder (for REST API).
      - Add-on resides on Search Head machine need not require any configuration here.
      - Add-on needs to be installed and configured on the Heavy Forwarder system.
      - Execute the following command on Heavy Forwarder to forward the collected data to the indexer. /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
      - On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
      - Add-on needs to be installed on Search Head for CIM mapping.

## Upgrading to version 2.9.0 from 2.8.0
- Follow the UPGRADE section.
- No additional steps are required.

## Upgrading to version 2.8.0 from 2.7.0
- Follow the UPGRADE section.
- No additional steps are required.

## Upgrading to version 2.7.0 from 2.6.0
- Follow the UPGRADE section.
- No additional steps are required.

## Upgrading to version 2.6.0 from 2.5.0
- Follow the UPGRADE section.
- No additional steps are required.

## Upgrading to version 2.5.0 from 2.4.0
- Follow the UPGRADE section.
- Bump the javascript in browser to load new javascript changes.
      - In browser update the URL like this: `<http/https>://<yoursplunk>/en-US/_bump`.
      - click on `Bump version` button.
      - Remove the `_bump` from the url and load the input page.
- No additional steps are required.

Configuration:
-------------------------------------------------------------------------------
* The VulnDB application has a straightforward configuration interface.  
* Before starting configuration of the application, you must have your VulnDB consumer API key, and consumer API secret in order to successfully add an input to Splunk for VulnDB vulnerability information.
* Before adding an input for VulnDB, please review the "Configuration" menu option to make sure you put in your proxy server settings (if necessary) and your logging level.
* Once the add-on is installed, you can navigate to it by clicking on the VulnDB app on the left side of the Splunk web interface.
* The first page that will appear is the Inputs page.
* Click on the "Create New Input" button on the upper right of the Inputs page.
* Fill in the information as requested on the Add vulndb input window:

| Field    | Description                                                 |
| -------- | ----------------------------------------------------------- |
| Name     | The name of the input you wish to create.  Ie; vulndb_input |
| Interval | The time interval in seconds between API requests to load data into Splunk (3600 = Every hour, 86400 = Once per day) (Recommended minimum 3600 secs) |
| Index    | The Splunk index that you want to ingest the vulnerability events into |
| API URL   | The URL to access the VulnDB API (the default should work, but this might change at some point)|
| API Key    | The VulnDB consumer key assigned from VulnDB.  You can get this from your VulnDB account: https://vulndb.flashpoint.io/users/sign_in |
| API Secret | The VulnDB consumer secret assigned from VulnDB.  You can get this from your account as well (see link above) | 
| Start date | The starting date that you want to use to gather vulnerability information from.  The API will return results that have vulnerabilities that were modified on or after this date. |
| Page size | The number of VulnDB results that the API should return in a single request.  The maximum is 100.  This means if there are 800 new vulnerabilities updated since the last run, and your page size is set to 100, the app will make 8 total API requests to the VulnDB API. |
| Reset Input | If for some reason, you need to re-ingest vulnerability information from the start date, you will have to check this box off in order to do so.  The app remembers the most recent date stamp, and by default will ignore the start date after the first run.|

* There are additional options available, which are documented in the VulnDB API reference manuals.
* When you are finished selecting all of your desired options, you can click on the "Add" button to add the input.  
* The input will start to contact the VulnDB API immediately.
* The first time the input runs, it may take a long period of time to see results in Splunk. Depending upon your start date, the input will be trying to retrieve 1000's or more vulnerability details.
* Please be patient, as the process takes time.  You can view activity in Splunk using a search:
   * index=_internal source=*ta_vuln_db_vulndb.log
* This will search the VulnDB application log file for events.  Depending upon the logging level selected, you will see various details about the input activity.

OPEN SOURCE COMPONENTS AND LICENSES
-------------------------------------------------------------------------------
* requests_oauthlib (LICENSE: https://github.com/requests/requests-oauthlib/blob/master/LICENSE)
* oauthlib: (LICENSE: https://github.com/oauthlib/oauthlib/blob/master/LICENSE)

TROUBLESHOOTING
-------------------------------------------------------------------------------

### General Checks
* Note that all log files of this App will be generated in `$SPLUNK_HOME/var/log/splunk/` directory.
* Check $SPLUNK_HOME/var/log/Splunk/<ta-log-name-prefix>*.log or user can search `index="_internal" source=*vuln_db*.log` query to see all the logs in UI. Also, user can use `index="_internal" source=*vuln_db*.log ERROR` query to see ERROR logs in the Splunk UI.
* To get the detailed logs, in the Splunk UI, navigate to VulnDB Add-on for Splunk. Click on Configuration and go to the Logging tab. Select the Log level to DEBUG.
* Disable and Re-enable the input to recollect the data. Check the logs, it will be more verbose and will give the insights on data collection.
* Getting "CVSSv2 score should be a number in range 0 to 10." error while cloning an input is a known error. Try creating a new input instead of cloning.
 
### If you are still having problems, use the command line and run this command to generate diag and send to VulnDB support
- `$SPLUNK_HOME/bin/splunk diag --collect app:TA-vuln-db`

### To troubleshoot VulnDB data collection
* Ensure that the internet is active (On a proxy machine, if proxy is enabled).
* check $SPLUNK_HOME/var/log/splunk/ta_vuln_db_vulndb.log log file. 

BINARY FILE DECLARATION
-------------------------------------------------------------------------------
* pvectorc.cpython-37m-x86_64-linux-gnu.so - This is binary file.
* _yaml.cpython-37m-x86_64-linux-gnu.so - This is a binary file.

SUPPORT
-------------------------------------------------------------------------------
* Support Offered: Yes
* Support Email : support@riskbasedsecurity.com
* Supported by Flashpoint team through Splunk Community on best effort

EULA
-------------------------------------------------------------------------------
<https://help.fp.tools/en/articles/6653242-end-user-license-agreement-eula>


Release Notes
-------------------------------------------------------------------------------

|Date|Version|Changes|
|----|----|----
|2018-05-22|1.0.0|1. Initial release
|2018-06-27|1.0.1|1. Corrected a memory issue for large API data volumes
|2018-09-28|1.0.2|1. Fixed Splunk Appcert issues
|2018-10-16|1.0.3|1. Added validation for Splunk's generic UI outside of the app
|2018-11-15|1.1.0|1. Added proxy support 
||| 2. Incorporated new logic for data collection using find_by_time API
||| 3. Implemented OAuth2 for data collection
||| 4. Removed support of Vulnerability Timeline and Exposure Metrics data collection from the Add-on to reduce API load on VulnDB server
||| 5. Resolved truncation issue for long events
|2019-04-24|1.2.0|1. Added feature to filter data using CVSSv2 score
|2019-09-16|1.3.0|1. Removed unnecessary logs
|2020-01-27|2.0.0|1. Added Splunk v8 support
||| 2. Made Add-on Python2 and Python3 compatible
|2020-03-11|2.0.1|1. Fixed AppInspect Failure
|2020-06-08|2.0.2|1. Fixed data collection paging issue
|2021-02-08|2.2.0|1. Changed the logo for VulnDB Splunk Add-on
||| 2. Changed the "Page size" limit on Inputs page to 100
|2021-15-09|2.4.0| Migrated to AoB 4
|2022-21-10|2.5.0| Migrated to AoB 4.1.1
|2023-05-08|2.6.0| 1. Updated API to v2 version.
||| 2. Included new scores in events.
||| 3. Updated the Add-on's label and logo.
|2024-12-04|2.7.0| 1. Migrated to AoB v4.2.0
|2024-09-10|2.8.0| 1. Changed Based URL to "vulndb.flashpoint.io".
||| 2. Upgraded Python SDK version to 2.0.2.
|2025-10-24|2.9.0| 1. Migrated to AoB v4.5.1
||| 2. Upgraded Python SDK version to 2.1.1

## Copyright 2025 Flashpoint