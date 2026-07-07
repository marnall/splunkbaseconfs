# ABOUT THIS APP

The Cisco Nexus 9k App for Splunk Enterprise is used to Build dashboard on indexed data provided by "Cisco Nexus 9k Add-on for Splunk Enterprise" app.

# REQUIREMENTS

* Splunk version supported 9.1.x, 9.2.x.
* This main App requires "Cisco Nexus 9k Add-on for Splunk Enterprise" version 3.0.0.

# Recommended System configuration

* Splunk search head system should have 8 GB of RAM and a quad-core CPU to run this app smoothly.
   
# Topology and Setting up Splunk Environment

* This app has been distributed in two parts.

  1) Add-on app, which runs collector scripts and gathers data from nexus 9k switches and also syslogs on udp port, does indexing on it and provides data to Main app.
  2) Main app, which receives indexed data from Add-on app, runs searches on it and builds dashboard using indexed data.

* This App can be set up in two ways:

  1) **Standalone Mode**: Install main app and Add-on app on a single machine.

     * Here both the app resides on a single machine.
     * Main app uses the data collected by Add-on app and builds dashboard on it

  2) **Distributed Environment**: Install main app and Add-on app on search head and only Add-on app on forwarder system.

      * Here also both the apps resides on search head machine, but no need to enable input scripts on search head.
      * Only Add-on app required to be installed on forwarder system.
      * Execute the following command to forward the collected data to the search head.
       $SPLUNK_HOME/bin/splunk add forward-server <search_head_ip_address>:9997
      * On Search head machine, enable event listening on port 9997 (recommended by Splunk).
      * Main app on search head uses the received data and builds dashboards on it.

# Installation of App

* This app can be installed either through UI through "Manage Apps" or by extracting zip file into /opt/splunk/etc/apps folder.
* The app data defaults to 'main' index.
* If you have created custom index for your Nexus 9k data follow below steps:
    1) If local folder does not exists, then create local folder inside $SPLUNK_HOME/etc/apps/cisco-app-Nexus-9k folder.
    2) Copy macros.conf file inside local folder from default folder.
    3) Replace  **definition = ()** with **definition = index = <your_index>** under nexus_index stanza.
* Restart Splunk

* **Note:** If the previous version of App is already installed, remove the cisco-app-Nexus-9k folder from Splunk app folder before installation of newer version or the user can upgrade the app from Splunk UI.

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

After successfully upgrading the App(cisco-app-Nexus-9k) follow the below steps.
* credentials.csv file will not be used for custom commands, User needs to follow below steps to configure the credentials.
  * Go to Manage Apps -> Search for Cisco Nexus 9k App for Splunk Enterprise
  * Click on setup under Action section
  * Configure IP/Hostname and password
  * User can configure multiple from the same setup page it will store the multiple values
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

* When app is installed or there is no local/passwords.conf file found, then user will be redirected to setup page containing ip address, username, password.He/She won't be able to view dashboards until credentials are not provided.
* If user wants to enter more credentials then he/she can go to Apps->Manage Apps->Set up cisco-app-Nexus-9k.It will open a set up screen which will ask for credentials.
* Splunk REST API will encrypt the password and store it in app itself(local/passwords.conf) in encrypted form, nxapicollector custom command will fetch these credentials through REST API to connect to the Nexus 9k.
* The app data defaults to 'https' scheme for all its calls between the Nexus 9k switch and Splunk.
* If your switch is http configured, perform below steps:
    1) If local folder does not exists, then create local folder inside $SPLUNK_HOME/etc/apps/cisco-app-Nexus-9k folder.
    2) Copy default/cisco_nexus_setup.conf file in your local folder.
    3) Change the value of HTTP_SCHEME to http in your local/cisco_nexus_setup.conf file.
    4) Restart Splunk.

* **Note:** Whenever user wants to change the credentials, he/she needs to remove the current entry from directory cisco-app-Nexus-9k/local/passwords.conf first, restart the splunk then provide the credentials through UI. (This time credentials will be asked when app is opened for first time.)

# TEST YOUR INSTALL

  After TA App is configured to receive data from nexus 9k switches, The main app dashboard can take some time before the data is populated in all panels. A good test to see that you are receiving all of the data is to run this search after several minutes:

    index=<your_index> | stats count by sourcetype

In particular, you should see this sourcetype:
* cisco:nexus:json


If you don't see these sourcetype, have a look at the messages output by the scripted input: Collect.py. Here is a sample search that will show them

  index=_internal component="ExecProcessor" collect.py "Nexus Error"| table _time host log_level message


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

2. d3.js  
  Link: https://d3js.org  
  Home Page: https://github.com/d3/d3  
  License :: BSD license  
  Operating System :: OS Independent  


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


# NX-API Collector(Custom Search Command Reports)

This app provides a generic NX-API collector which empowers users to make use of NX-API provided by Nexus 9k and periodically track certain data from 9k switch. It simply takes switch CLI and convert it into NX-API call and provide data which can be saved as a dashboard.

Every time the saved dashboard is clicked, splunk makes a call to switch using NX-API and fetch current data for that dashboard. Note that this data will not be saved in splunk database.

Please follow below given steps to generate custom command reports.

1) Go to search option and enter your search in search bar.
   You have different option for custom search command:

   * | nxapicollect command="your cli" (Make sure credentials for this devices are already configured through setup page and your command will fetch credentials for switch from Splunk's \storage\passwords endpoint)
   * | nxapicollect command="your cli" device="x.x.x.x"
   * | nxapicollect command="your cli" device="x.x.x.x,y.y.y.y"
   * | nxapicollect command="your cli" device="x.x.x.x" username="username" password="password"

2) Click on Save As and click on Dashboard Panel to store your result in dashboard.

3) Enter Dashboard Title. You have to give "report" keyword in giving dashboard title.

4) You can see your dashboard in Custom reports.(In menu bar)


# Saved Searches

This app provide savedsearches which generate lookup files or provides interface details.

* savedsearches which generates lookup files
  * hostname - generates hostname.csv file
  * moduleSwHwVersion - generates inventory_modinf.csv file
  * powerStatus - generates powerStatus.csv file
  * temperature - generates temperatureLookup.csv file
  * version - generates version.csv file

* savedsearch which provide interface details
  * Interface_Details - provide details of all the physical interfaces

# Troubleshooting

* In order to troubleshoot any issues with the custom commands, a separate log file would be available which contains the log messages corresponding to the data collection. In order to see the logs, navigate to $SPLUNK_HOME/var/log/splunk/cisco_app_nexus_9k_collect.log file.
  * If you want to update the log level to other levels such as DEBUG, ERROR, etc. update the **loglevel** param of the cisco_nexus_setup.conf file inside $SPLUNK_HOME/etc/apps/cisco-app-Nexus-9k/local folder.
* By default, the API calls to the Nexus switch would be done by the SSL verification. If you want to make Insecure HTTP calls, change the SSL verification to False. In order to do that, navigate to $SPLUNK_HOME/etc/apps/cisco-app-Nexus-9k/local/cisco_nexus_setup.conf file and change the **verify_ssl** parameter value to False.
  * If you want to add custom SSL certificate to the certificate chain, create a .pem file and provide the absoulte path of the .pem file in the **ca_certs_path** param of the cisco_nexus_setup.conf file.

# Release Notes

v3.0.0
* Added support of Splunk 9.1.x, 9.2.x.
* Added support for NXOS v9.3(9), 9.3(8), 10.3(4a), 10.4(3).
* Enhanced logging for better debugging.  

v2.1.0
* Updated setup guide
* Added support of Splunk 8.x

v2.0.1
* Added setup page for credentials configuration to store in storage/passwords
* Added few drilldowns to show table events for more insights
* Removed credentials.csv support to suffice cloud cert checks
* Removed default lookup files that are generated by savedsearches