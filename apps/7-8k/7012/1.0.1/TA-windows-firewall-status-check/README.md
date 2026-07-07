# Windows Firewall Status Check Add-on for Splunk

### Download from Splunkbase
https://splunkbase.splunk.com/app/7012


OVERVIEW
--------
The Windows Firewall Status Check Add-on for Splunk allows users to check their Windows machine's firewall status. It uses the PowerShell script to collect the latest status of Windows Firewall based on Netsh command. The Add-on does not contain any dashboards or savedsearches.

Install the Cyences App for Splunk (https://splunkbase.splunk.com/app/5351/) to get alerts and dashboards related to the data collected by this Add-on.

* Author - CrossRealms International Inc.
* Creates Index - False
* Compatible with:
   * Splunk Enterprise version: 10.0.x, 9.4.x, 9.3.x, 9.2.x, 9.1.x, 9.0.x
   * OS: Platform Independent
   * Browser: Does not have UI.


## What's inside the App

* No of Custom Inputs: **1**



TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
------------------------------------------
There are two ways to setup this app:
  1. Standalone Mode: 
     * Install the `Windows Firewall Status Check Add-on`.
  2. Distributed Mode:
     * The Add-on is required on the Search Head for field extraction. Input configuration is not required on the Search Head.
     * Install the `Windows Firewall Status Check Add-on` on the Universal Forwarders on Windows and configure it. (You could do that from Deployment Server.)
     * Install the Add-on on a heavy forwarder if forwarders are sending data to Heavy Forwarder, otherwise install it on Indexers for data parsing. Input configuration is not required for both indexers and heavy forwarders.


DEPENDENCIES
------------------------------------------------------------
* There are no external dependencies for this Add-on.


INSTALLATION
------------------------------------------------------------
* From the Splunk Home page, click the gear icon next to Apps.
* Click `Browse more apps`.
* Search for `Windows Firewall Status Check Add-on`.
* Click `Install`.
* If prompted, restart Splunk.


DATA COLLECTION & CONFIGURATION
------------------------------------------------------------
### Enable Data Inputs ###
* Add the following stanzas in `TA-windows-firewall-status-check/local/inputs.conf` file and deploy it for all required Windows hosts.
```
[powershell://windows_firewall_status_check]
disabled = 0
```
NOTE: Data will be collected in the 'windows' index by default, so ensure that index is created before enabling the input.

UNINSTALL ADD-ON
-------------
1. SSH to the Splunk instance.
2. Navigate to apps ($SPLUNK_HOME/etc/apps).
3. Remove the `TA-windows-firewall-status-check` folder from the `apps` directory.
4. Restart Splunk.


RELEASE NOTES
-------------
Version 1.0.1 (September 2025)
* Minor document change.

Version 1.0.0 (July 2023)
* Created Add-on with Powershell script and required configuration to collect the data.



OPEN SOURCE COMPONENTS AND LICENSES
------------------------------
* N/A


CONTRIBUTORS
------------
* Vatsal Jagani
* Mahir Chavda
* Hardik Dholariya
* Madhav Pandya



SUPPORT
-------
* Contact - CrossRealms International Inc.
  * US: +1-312-2784445
* License Agreement - https://d38o4gzaohghws.cloudfront.net/static/misc/eula.html
* Copyright - Copyright 2025 CrossRealms International
