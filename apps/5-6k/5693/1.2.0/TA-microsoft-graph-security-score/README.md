# Microsoft Graph Security Score Add-on for Splunk

### Download from Splunkbase
https://splunkbase.splunk.com/app/5693


OVERVIEW
--------
The Microsoft Graph Security Score Add-on for Splunk allows users to collect their Azure (Office 365) Security Score from Microsoft's Security Graph API. It consists of Python scripts that collect the required/necessary data to configure the account information.

* Author - CrossRealms International Inc.
* Creates Index - False
* Compatible with:
   * Splunk Enterprise version: 9.1.x, 9.0.x, 8.2.x
   * OS: Platform Independent
   * Browser: Google Chrome, Mozilla Firefox, Safari


## What's inside the App

* No of XML Dashboards: **3**
* Approx Total Viz(Charts/Tables/Map) in XML dashboards: **4**
* No of Custom Inputs: **1**



TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
------------------------------------------
There are two ways to setup this app:
  1. Standalone Mode: 
     * Install the `Microsoft Graph Security Score Add-on for Splunk`.
  2. Distributed Mode:
     * The Add-on can be installed on search head, but it is not required. The Add-on configuration is not required on search head. (The Add-on contains a dashboard to show Microsoft Graph Security Score.)
     * Install the `Microsoft Graph Security Score Add-on for Splunk` on the heavy forwarder.
     * Configure the Add-on to collect the required information from the Microsoft Graph API on the heavy forwarder.
     * The Add-on do not support universal forwarder.
     * The Add-on is not required on an indexer.


DEPENDENCIES
------------------------------------------------------------
* There are no external dependencies for this Add-on.


INSTALLATION
------------------------------------------------------------
The Add-on needs to be installed on the Search Head and heavy forwarder.

* From the Splunk Home page, click the gear icon next to Apps.
* Click `Browse more apps`.
* Search for `Microsoft Graph Security Score Add-on`.
* Click `Install`.
* If prompted, restart Splunk.


DATA COLLECTION & CONFIGURATION
------------------------------------------------------------
### Configuration Required on Azure###
* Configure Tenant(Directory) ID, Application(Client) ID, Client Secret in Azure Active Directory.
    * Reference - https://www.inkoop.io/blog/how-to-get-azure-api-credentials/
* Add the below permission to the Application.
    * Microsoft Graph > Application > SecurityEvents.Read.All & SecurityEvents.ReadWrite.All
    * Reference - https://docs.microsoft.com/en-us/graph/api/securescore-get?view=graph-rest-1.0&tabs=http


### Configure Data Input ###
1. Navigate to `Microsoft Graph Security Score Add-on for Splunk` > `Input` on Splunk UI.
2. Click on `Create New Input`.
3. Add the following parameters:

| Parameter | Description |
| --- | --- |
| Name | Enter a unique name for the input. |
| Interval | Interval in seconds (how often the Add-on should collect the latest data from the Microsoft Graph API). The ideal value is between 3600 (1 hour) - 14400 (4 hours) |
| Index | Enter the index name in which the Graph API data will be stored in Splunk. |
| Azure AD Tenant ID | Obtain the Tenant ID (Directory) from Azure AD. |
| Application Id | Obtain the Application ID (Client) from Azure AD. |
| Client Secret | Obtain the Client Secret from Azure AD. |


4. Click on `Save`.



UNINSTALL ADD-ON
-------------
1. SSH to the Splunk instance.
2. Navigate to apps ($SPLUNK_HOME/etc/apps).
3. Remove the `TA-microsoft-graph-security-score` folder from the `apps` directory.
4. Restart Splunk.


RELEASE NOTES
-------------
Version 1.2.0 (Aug 2024)
* Added proxy support
* Upgraded addon to use latest UCC v5.48.2

Version 1.1.1 (Jul 2023)
* Changed checkpoint file location to make addon cloud compatible.

Version 1.1.0 (Jul 2023)
* Upgraded the addon to UCC latest v5.28.1

Version 1.0.1 (Aug 2021)
* Changes to make compatible with the latest Splunk AppInspect - Dashboards version changed to 1.1.


Version 1.0.0 (Aug 2021)
* Created Add-on by UCC Splunk-Python library.
* Added the configuration pages.



OPEN SOURCE COMPONENTS AND LICENSES
------------------------------
* The Add-on is built using UCC framework (https://pypi.org/project/splunk-add-on-ucc-framework/).

This is an add-on powered by the Splunk Add-on Builder.
## Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-microsoft-graph-security-score/bin/ta_microsoft_graph_security_score/aob_py3/pvectorc.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-microsoft-graph-security-score/bin/ta_microsoft_graph_security_score/aob_py3/setuptools/gui-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-microsoft-graph-security-score/bin/ta_microsoft_graph_security_score/aob_py3/setuptools/cli-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-microsoft-graph-security-score/bin/ta_microsoft_graph_security_score/aob_py3/setuptools/gui.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-microsoft-graph-security-score/bin/ta_microsoft_graph_security_score/aob_py3/setuptools/gui-32.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-microsoft-graph-security-score/bin/ta_microsoft_graph_security_score/aob_py3/setuptools/cli-64.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-microsoft-graph-security-score/bin/ta_microsoft_graph_security_score/aob_py3/setuptools/cli.exe: this file does not require any source code
/opt/splunk/var/data/tabuilder/package/TA-microsoft-graph-security-score/bin/ta_microsoft_graph_security_score/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code


CONTRIBUTORS
------------
* Bhavik Bhalodia
* Vatsal Jagani
* Usama Houlila
* Preston Carter
* Ahad Ghani
* Hardik Dholariya



SUPPORT
-------
* Contact - CrossRealms International Inc.
  * US: +1-312-2784445
* License Agreement - https://d38o4gzaohghws.cloudfront.net/static/misc/eula.html
* Copyright - Copyright CrossRealms Internationals, 2023
