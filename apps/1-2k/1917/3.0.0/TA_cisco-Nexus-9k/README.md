# ABOUT THIS APP
  The Cisco Nexus 9k Add-on for Splunk Enterprise provides a scripted input for Splunk that automatically extracts response of CLI commands of Cisco Nexus 9000 Switches.Moreover, this app gathers Syslog from Cisco Nexus 9000 Switches and provide the same to the main app.

# REQUIREMENTS

* Splunk version supported 9.1.x, 9.2.x.
* The indexer system must have network access (HTTP/HTTPS) to one or more nexus 9k switches which are to be Splunked.
* Admin user ID and password for collecting data from nexus 9k switches.
* This main Add-on requires "Cisco Nexus 9k App for Splunk Enterprise" version 3.0.0.


# Recommended System configuration
Splunk indexer system should have 4 GB of RAM and a quad-core cpu to run this app smoothly

# Topology and Splunk Environment setup

* This app has been distributed in two parts.

  1) Add-on app, which runs collector scripts and gathers data from ACI environment, does indexing on it and provides indexed data to Main app.
  2) Main app, which receives indexed data from Add-on app, runs searches on it and builds dashboard using indexed data.

* This App can be set up in two ways:
  1) **Standalone Mode**: Install main app and Add-on app on a single machine.

     * Here both the app resides on a single machine.
     * Main app uses the data collected by Add-on app and builds dashboard on it

  2) **Distributed Environment**: Install main app and Add-on app on search head and only Add-on app on forwarder system.

    * Here also both the apps resides on search head machine, but no need to enable input scripts on search head.
    * Only Add-on app required to be installed on forwarder system.
    * Execute the following command to forward the collected data to the search head.
      /opt/splunk/bin/splunk add forward-server <search_head_ip_address>:9997
    * On Search head machine, enable event listening on port 9997 (recommended by Splunk).
    * Main app on search head uses the received data and builds dashboards on it.

# Installation of App

* This app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.
* Enable Data collector Scripts using input.conf (default disabled = 0) or through UI (Settings -> DataInputs -> Scripts).
* Restart Splunk.

* **Note:** If the previous version of App is already installed, remove the TA_cisco-Nexus-9k folder from Splunk app folder before installation of newer version or the user can upgrade the app from Splunk UI.

# Upgradation of App/Add-on
  Please disable all the scripted inputs before upgrading Add-on(TA_cisco-Nexus-9k).
* Download the App package
* From the UI navigate to `Apps->Manage Apps`
* In the top right corner select "Install app from file"
* Select "Choose File" and select the App package
* Check Upgrade App
* Select "Upload" and follow the prompts.
  #### OR
* If newer version is available on splunkbase, then App/Add-on can be updated from UI also.
  * From the UI navigate to `Apps->Manage Apps` OR click on gear icon
  * Search for Cisco Nexus 9k App/Add-on
  * Click on `'Update to <version>'` under Version Column.

# Post upgradation steps

After successfully upgrading the Add-on(TA_cisco-Nexus-9k) follow the below steps.
* If the app is upgraded from version 1.0/1.1 to the latest version, the user needs to create custom index named "n9000", because on upgrading "n9000" index will be deleted so index needs to created for searching data and also indexing new coming data.
* Steps to create custom index is mentioned in section: Create your own index.
* If Add-on in configured on Windows environment, perform following steps:
  * Copy the content of "default/inputs.conf.WINDOWS to default/inputs.conf" 

# Uninstallation of App

This section provides the steps to uninstall App from a standalone Splunk platform installation.

* (Optional) If you want to remove data from Splunk database, you can use the below Splunk CLI clean command to remove indexed data from an app before deleting the app.
  * $SPLUNK_HOME/bin/splunk clean eventdata -index <index_name>

* Delete the app and its directory. The app and its directory are typically located in the folder$SPLUNK_HOME/etc/apps/<appname> or run the following command in the CLI:
  * $SPLUNK_HOME/bin/splunk remove app [appname] -auth <splunk username>:<splunk password>

* You may need to remove user-specific directories created for your app by deleting any files found here: $SPLUNK_HOME/bin/etc/users/*/<appname>

* Restart the Splunk platform.You can navigate to Settings -> Server controls and click the restart button in splunk web UI or use the following splunk CLI command to restart splunk:
  * $SPLUNK_HOME/bin/splunk restart

# Configuration of App

* After installation, go to the Apps->Manage Apps->Set up TA_cisco-Nexus-9k.It will open a set up screen which will ask for Nexus 9k credentials.Please provide ip address, username, password and save them.You can add as many switch details as you want.
* Splunk REST API will encrypt the password and store it in app itself(local/passwords.conf) in encrypted form, Data collector script will fetch these credentials through REST API to connect to the Nexus 9k.
* The app data defaults to 'https' scheme for all its calls between the Nexus 9k switch and Splunk.
* If your switch is http configured, perform below steps:
    1) If local folder does not exists, then create local folder inside $SPLUNK_HOME/etc/apps/TA_cisco-Nexus-9k folder.
    2) Copy default/cisco_nexus_setup.conf file in your local folder.
    3) Change the value of HTTP_SCHEME to http in your local/cisco_nexus_setup.conf file.
    4) Restart Splunk.

## inputs.conf

This file contains filename paths which are different based on your OS platform. The app is configured out of the box to work for Unix/Linux/Mac OS systems. If you are running this app on a Windows system, perform the following steps:
1. Copy the content of "default/inputs.conf.WINDOWS to default/inputs.conf"  
2. Now, Copy and Paste that default/inputs.conf to local/inputs.conf  
3. Restart Splunk  

* Each entry in this file contains one field with name passAuth and its default value is admin.Basically, value of this field is used by collector script to fetch the credentials of Nexus 9k through REST API.User can assign any splunk username here but please make sure that username is having admin privileges to access the credentials through REST API.


# TEST YOUR INSTALL

  After TA App is configured to receive data from nexus 9k switches, The main app dashboard can take some time before the data is populated in all panels. A good test to see that you are receiving all of the data is to run this search after several minutes:

    index=main | stats count by sourcetype

In particular, you should see this sourcetype:
* cisco:nexus:json


If you don't see these sourcetype, have a look at the messages output by the scripted input: Collect.py. Here is a sample search that will show them
* index=_internal component="ExecProcessor" collect.py "Nexus Error"| table _time host log_level message

If you are using this App/Add-on on Windows environment, then also take a look at output of following search query:
* index=_internal component=ConfPathMapper TA_cisco-Nexus-9k

  if you get `Access Denied` error in output like:

  `WARN  ConfPathMapper - Failed to open: C:\Program Files\Splunk\etc\apps\TA_cisco-Nexus-9k\local\cisco_nexus_setup.conf: Access is denied.`

  Then, you need to change the permission of cisco_nexus_setup.conf file under TA_cisco-Nexus-9k\local folder. follow below steps.
  * Right Click on local/cisco_nexus_setup.conf -> properties -> security. if there is no permission for SYSTEM then follow below steps. 
  * Right Click on local/cisco_nexus_setup.conf -> properties -> security -> click on Edit -> Add -> enter "SYSTEM" in box area -> click Check Names -> OK -> under Permission for SYSTEM Allow it Full Control -> OK
  * Same way give Read Permission to “Everyone“
  * Restart Splunk


# Create your own index:

* The app data defaults to 'main' index.
* If you need to specify a particular index for your Nexus 9k data, for ex. 'n9000' follow below steps:
    1) If local folder does not exists, then create local folder inside $SPLUNK_HOME/etc/apps/TA_cisco-Nexus-9k folder.
    2) Create an indexes.conf file inside local folder.
    3) Add following stanza inside indexes.conf file (when index name is n9000):
        [n9000]
        coldPath = $SPLUNK_DB/n9000/colddb
        homePath = $SPLUNK_DB/n9000/db
        thawedPath = $SPLUNK_DB/n9000/thaweddb
    4) Restart Splunk.
* Once you specify your index, edit the inputs.conf file and add a line **index =** <**your_index>** under each script stanza.


# The list of Python library used

1. Xmltodict Client Library
	Link: https://pypi.org/project/xmltodict/
	Author: Martin Blech
	Home Page: https://github.com/martinblech/xmltodict
	License :: OSI Approved :: MIT License
  Operating System :: OS Independent
  Programming Language :: Python
  Programming Language :: Python :: 2
  Programming Language :: Python :: 2.7
  Programming Language :: Python :: 3
  Programming Language :: Python :: 3.4
  Programming Language :: Python :: 3.5
  Programming Language :: Python :: 3.6
  Programming Language :: Python :: 3.7


# Integration of Nexus 9k syslog messages with Splunk

  1) **Configure from UI**

  * Go to Settings->Data Inputs and click on UDP
  * Click on New Local UDP to create UDP data input
  * Configure UDP Port=514 for syslog
  * Click on Next button
  * Select Sourcetype=syslog, App Context=Cisco Nexus 9k Add-on for Splunk Enterprise and index = your_index
  * Click on Review button
  * Click on Submit button

  2) **Configure from Backend**

  * Add/Update inputs.conf in $SPLUNK_HOME/etc/apps/TA_cisco-Nexus-9k/local folder
  * Enter below content to inputs.conf
            [udp://514]
            index = <your_index>
            sourcetype = syslog
            disabled = 0
  * Restart Splunk

  **NOTE:** If you want to index data in different sourcetype, perform below steps:

  * Change below content in $SPLUNK_HOME/etc/apps/TA_cisco-Nexus-9k/local/inputs.conf
          [udp://514]
          index=<your_index>
          sourcetype = <your_sourcetype>
          disabled = 0
  * Copy the content from $SPLUNK_HOME/etc/apps/TA_cisco-Nexus-9k/default/eventtypes.conf to $SPLUNK_HOME/etc/apps/TA_cisco-Nexus-9k/local/eventtypes.conf
  * Change the sourcetype in your local/eventtypes.conf
          [cisco_nexus_syslog]
          search = sourcetype = <your_sourcetype>
  * Restart Splunk


# ABOUT THE DATA


Field names are case sensitive in the nexus 9k. Every event starts with the timestamp, and always contains device from which that particular event came.For simplification we can add one additional field in each event  named "component" and provide appropriate value to it so that we can easily segregate the data on the basis of its component name.

Below are two sample event records. First one gives system resource details in Json format and the other one gives accounting logs in key=value form as a raw data.

1)

{"device": "x.x.x.x", "timestamp": "2014-06-23 01:20:19", "Row_info": {"cpuid": "0", "kernel": "0.99", "idle": "99.00", "user": "0.00"}, "component": "nxresource"}
{"device": "x.x.x.x", "timestamp": "2014-06-23 01:20:19", "Row_info": {"cpuid": "1", "kernel": "0.00", "idle": "100.00", "user": "0.00"}, "component": "nxresource"}
{"device": "x.x.x.x", "timestamp": "2014-06-23 01:20:19", "Row_info": {"cpuid": "2", "kernel": "0.00", "idle": "100.00", "user": "0.00"}, "component": "nxresource"}
{"device": "x.x.x.x", "timestamp": "2014-06-23 01:20:19", "Row_info": {"cpuid": "3", "kernel": "0.00", "idle": "100.00", "user": "0.00"}, "component": "nxresource"}

2)

{"device": "x.x.x.x", "Row_info": {"hw": "0.1010", "sw": "6.1(2)I2(2a)", "modwwn": "1", "slottype": "LC1"}, "timestamp": "2015-01-01 09:05:08", "component": "nxinventory"}


# DATA GENERATOR
This app is provided with sample data which can be used to generate dummy data. To simulate this sample data, first of all Splunk Event generator, which is available at https://github.com/splunk/eventgen, needs to be installed at $SPLUNK_HOME/etc/apps/. This app generates the dummy data for Cisco Nexus 9k switches and populates the dashboards of main app with the dummy data.

# Troubleshooting

* In order to troubleshoot any issues with the data collection, a separate log file would be available which contains the log messages corresponding to the data collection. In order to see the logs, navigate to $SPLUNK_HOME/var/log/splunk/TA_cisco-Nexus-9k_collect.log file.
  * If you want to update the log level to other levels such as DEBUG, ERROR, etc. update the **loglevel** param of the cisco_nexus_setup.conf file inside $SPLUNK_HOME/etc/apps/TA_cisco-Nexus-9k/local folder.
* By default, the API calls to the Nexus switch would be done by the SSL verification. If you want to make Insecure HTTP calls, change the SSL verification to False. In order to do that, navigate to $SPLUNK_HOME/etc/apps/TA_cisco-Nexus-9k/local/cisco_nexus_setup.conf file and change the **verify_ssl** parameter value to False.
  * If you want to add custom SSL certificate to the certificate chain, create a .pem file and provide the absoulte path of the .pem file in the **ca_certs_path** param of the cisco_nexus_setup.conf file.

# Release Notes

v3.0.0
* Added support of Splunk 9.1.x, 9.2.x.
* Added support for NXOS v9.3(9), 9.3(8), 10.3(4a), 10.4(3).
* Enhanced logging for better debugging.  

v2.1.0
* Added support of Splunk 8.x
* Made Add-on Python2 and Python3 compatible

v2.0.1
* Added validation on setup page to suffice cloud cert checks
* Provided backend configurable http_scheme for on-prem user who wants to collect data over an unencrypted network