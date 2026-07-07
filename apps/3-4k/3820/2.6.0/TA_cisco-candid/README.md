# About Cisco Network Assurance Engine (CNAE)
Cisco Network Assurance Engine is an intent assurance appliance for Data Center fabrics which raises issues or concerns as Smart Events against the Intent specified and provides information on what could be affecting the underlying infrastructure configurations, helping mitigate the direct impact on daily business services. 
This rich information is discovered through RESTful interfaces provided by Cisco NAE to index in Splunk.
The Cisco Candid App for Splunk Enterprise offers interactive and insightful dashboards to Candid users to:
 1.) Track Smart Events over epochs,
 2.) View event changes across epochs reported by CNAE Intent Assurance software,
 3.) Inspect new, persisted, resolved and , unresolved events.
 4.) Epoch and Event delta analysis

# REQUIREMENTS

* Splunk version supported 7.2, 7.3 and 8.0
* NAE version supported 4.1, 5.0, and 5.1.
* This main Add-on requires "Cisco NAE App for Splunk Enterprise" version 2.5.0

# Recommended System configuration

* Splunk search head system should have minimum 16 GB of RAM and a octa-core CPU to run this app smoothly.


# Topology and Setting up Splunk Environment
  
 1)  Install the main app (Cisco NAE App for Splunk Enterprise) and Add-on app (Cisco NAE Add-on for Splunk Enterprise) on a single machine or a distributed environment.
* Here both the app resides on a single machine.
* Main app uses the data collected by Add-on app and builds dashboard on it
 2) Install the main app (Cisco NAE for Splunk Enterprise) on Search Head and Add-on app (Cisco NAE Add-on for Splunk Enterprise) on Indexer/Forwarder
 * Here both the app resides on different machines.
 * Main app uses the data collected by Add-on app and builds a dashboard on it. Ensure that the index '<defaults to "main">' is searchable by the Search Head


* This app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.
* Restart Splunk.
* Login to Splunk: http://<your_splunk_host:port>
* Open browser: http://<your_splunk_host:port>/en-US/debug/refresh. Click "Refresh"
* Open browser: http://<your_splunk_host:port>/en-US/_bump 
    (To pull all updated web resources from the server to the browser, to modify the cached items such as js, cookies, images, etc..)
* Restart Splunk

# Installation of Add-on

* This Add-on app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder. 

# Upgradation of App/Add-on
  Please disable all the scripted inputs before upgrading Add-on(TA_cisco-candid).
* Download the App package
* From the UI navigate to `Apps->Manage Apps`
* In the top right corner select "Install app from file"
* Select "Choose File" and select the App package 
* Check Upgrade App
* Select "Upload" and follow the prompts.
  #### OR
* If a newer version is available on splunkbase, then App/Add-on can be updated from UI also.
  * From the UI navigate to `Apps->Manage Apps` OR click on gear icon
  * Search for Cisco NAE App/Add-on
  * Click on `'Update to <version>'` under Version Column.

# Post upgradation steps
####  Upgrading the Add-on(TA_cisco-candid) to v2.6.0 from any version

Please follow the below steps.

* If you have an add-on installed in the Windows environment and there is a last_pull_epoch_time.txt file under TA_cisco-candid/local folder, then perform the following steps.
  * Check the permission of last_pull_epoch_time.txt file: 
    * Right Click on local/last_pull_epoch_time.txt.
    * Navigate to Properties -> Security.
    * Check the permission for SYSTEM.
  * If there is no permission for SYSTEM then follow the below steps:
    * If scripted input is already enabled then first disable it.
    * Right Click on local/last_pull_epoch_time.txt.
    * Navigate to Properties -> Security.
    * Click on the Edit button.
    * Click on the Add button.
    * Enter <b> SYSTEM </b> in <em> Enter the object names to select </em> box.
    * Click Check Names.
    * Click on the OK button (in the new window prompted by check names).
    * Again, click on the OK button (in window where you entered SYSTEM).
    * Under <em> Permissions for SYSTEM </em> allow it Full Control.
    * Click on OK button (in window where you are giving permission).
    * Again, click on the OK button.
    * Restart splunk
    * Enable the scripted input.

  * If you want to disable data collection of lifecycle events after upgrading:
    * If scripted input is already enabled then first disable it.
    * Remove the configured stanza from passwords.conf
    * Restart Splunk
    * Again, configure the removed stanza as per guidelines mentioned in section: Configuration of Add-on
    * Restart Splunk
    * Enable the scripted input.

# Uninstallation of App

  This section provides the steps to uninstall App from a standalone Splunk platform installation.

  * (Optional) If you want to remove data from the Splunk database, you can use the below Splunk CLI clean command to remove indexed data from an app before deleting the app.
    * $SPLUNK_HOME/bin/splunk clean eventdata -index <index_name>

  * Delete the app and its directory. The app and its directory are typically located in the folder$SPLUNK_HOME/etc/apps/<appname> or run the following command in the CLI:
    * $SPLUNK_HOME/bin/splunk remove app [appname] -auth <splunk username>:<splunk password>

  * You may need to remove user-specific directories created for your app by deleting any files found here: $SPLUNK_HOME/bin/etc/users/*/<appname>

  * Restart the Splunk platform.You can navigate to Settings -> Server controls and click the restart button in splunk web UI or use the following splunk CLI command to restart splunk:
    * $SPLUNK_HOME/bin/splunk restart

# Configuration of Add-on

* After installation, Go to the Apps->Manage Apps and open "Setup" screen for Cisco NAE Add-on for Splunk Enterprise.
* It will open a  set up screen which will ask for NAE credentials.

  * The app provides 2 different modes to collect the data in Splunk. The common fields are NAE Hostname or IP address, Username and Collect Epochs from last n hours.
  * Mention total no. of hours to go back and fetch data from NAE (Default is set to '4' hours) in Collect Epochs from last n hours field.
  * One can enable/disable the option to collect the data for Smart Event Lifecycle. By default the checkbox for collecting Smart Event Lifecycle would be unchecked.
  * The different modes are:

  * Local User Authentication
    * The user can configure the app using the default approach i.e. using Password.

    * To setup NAE with Local User Authentication, follow the below given steps.
      * On the setup screen, enable the "Local User Authentication" checkbox.
      * Enter NAE hostname or IP address.
      * Enter hours to go back and collect epoch.
      * Enter username and password which is used to login to the NAE.
      * Click on the Save button at the bottom of the page.

  * Remote User Authentication
    * The user needs to provide both Password and Domain Name of User specified.

    * To setup NAE with Remote User Authentication, follow the below given steps.
      * On the setup screen, enable the "Remote User Authentication" checkbox.
      * Enter NAE hostname or IP address.
      * Enter hours to go back and collect epoch.
      * Enter username and password which is used to login to the NAE.
      * Enter the domain name of user.
      * Click on the Save button at the bottom of the page.

    ### **SSL Configuration:**
    * By Default SSL Verification is Enabled
    * To Disable SSL Verification follow the below steps:
        * After successfully configuring through setup page, passwords.conf file will be created under TA_cisco-candid/local folder
        * It will contain stanza like: [credential:&lt;nae_host&gt;:&lt;username&gt;,&lt;1 or 0&gt;,<b>&lt;**True**&gt;</b>,&lt;epoch_hour&gt;:]
        * Change **True** to **False** to disable SSL Verification
        * Restart Splunk

    ### **Enable/ Disable Smart Event Lifecycle**
    * To Enable / Disable Smart Event Lifecycle follow the below steps: 
      * After successfully configuring through setup page, passwords.conf file will be created under TA_cisco-candid/local folder
      * It will contain stanza like: [credential:&lt;nae_host&gt;:&lt;username&gt;,<b>&lt;1 or 0&gt;</b>,&lt;True&gt;,&lt;epoch_hour&gt;:]
      * If the checkbox is checked then **1** will be stored in the stanza and if the checkbox is unchecked then **0** will be stored in the stanza.
      * Change **1** to **0** to disable the collection for Smart Event Lifecycle.
      * Change **0** to **1** to enable the collection for Smart Event Lifecycle.
      * Restart Splunk

    ### **Configuring No of threads , Log Level , Timeout , Pagesize for response**
    * Navigate to "default/app_config.conf" or copy file to "TA_cisco-candid/local" folder .
    * By default, the value for number of threads per NAE would be 32 . Change it to any value of requirement.
    * By default, the log level would be set to " INFO ". One can change it to any log level and according to that, the logs will be displayed in candid_data_collection.log.
    * By default, the value for timeout is set to 120. Change it to any value of requirement.
    * By default, the page size is set to 200 . Change it to any value of requirement.
    * Restart Splunk



* Enable the collector script: Go to Settings> Data Inputs>Scripts, enable the script '$SPLUNK_HOME/etc/apps/TA_cisco-candid/bin/collectCandid.py -candid'  
   The time interval for the script is 900 seconds by default.

* NAE Hostname or IP address once configured to any 2 modes of authentication, cannot be configured through the remaining mode of authentication.

* Also, users can setup NAE either using any one of the two modes of authentication or all the two modes one by one but for different NAEs.
* Example: User can either setup only NAE1 using Local/Remote User Authentication.
					  OR
  User can setup NAE1 for Local User Authentication, NAE2 for Remote User Authentication

*  Whenever the user wants to change the credentials, he/she needs to remove the current entry from directory TA_cisco-candid/local/passwords.conf first.
   Restart Splunk. Provide the credentials through UI.

*  User also needs to modify "default/inputs.conf" according to the following guidelines.


inputs.conf
===============
This file contains filename paths that are different based on your OS platform.
The app is configured out of the box to work for Unix/Linux/macOS systems.

If you are running this app on a Windows system, perform the following steps:
  Copy the file "default/inputs.conf.WINDOWS" to "local/inputs.conf"

* The entry in default/input.conf contains a field "passAuth" with default value admin. This field can contain any splunk user with admin rights.

# Create your own index:

  * The app data defaults to the 'main' index.
  * If you need to specify a particular index for your NAE data, for ex. "candid",create an indexes.conf file [sample shown in ($SPLUNK_HOME/etc/apps/TA_cisco-candid/default/indexes.conf.sample)]
  * Once you specify your index, edit the inputs.conf file and add a line "index=[yourindex]" under each script stanza.
  * **Note:** The Splunk user needs to be able to search the defined index. You can do so by editing the user role and adding the defined index to be searched by default.

# The list of Python library packaged
1.  jsonpickle:  
    version: 0.9.5  
    Link: https://pypi.org/project/jsonpickle/  
    Home Page: https://jsonpickle.github.io/  
    Author: David Aguilar  
    License :: OSI Approved :: BSD License  
    Operating System :: OS Independent  
    Programming Language :: Python :: 2  
    Programming Language :: Python :: 3  



# TEST YOUR INSTALL

* Once  Add-on app  is configured to receive data from CNAE, The main app dashboard can take some time before the data is populated in all panels. A good test to see that you are receiving all of the data is to run this search after several minutes:

    index="<your index>" | stats count by sourcetype

In particular, you should see the sourcetype:
* cisco:candid:events

If you don't see these sourcetypes, have a look at the messages output by the scripted input: collectiCandid.py. Here is a sample search that will show them:

  index=_internal component="ExecProcessor" collectCandid.py "CNAE Error:" | table _time host log_level message


# Data Generator

* This app is provided with sample data which can be used to generate dummy data. To simulate this sample data, the Splunk Event generator, which is available at https://github.com/splunk/eventgen, needs to be installed at $SPLUNK_HOME/etc/apps. This APP uses the Samples provided in NAE Add-on app to populate the dummy data for NAE environment


# Support

* This app is supported by Cisco Systems.
* Email support during weekday business hours. Please ask question or send an email to cisco-dcn-splunk-app-owners@cisco.com

# Release Notes
* Version 2.6.0:
  * Compatibility with NAE v5.1
  * Added Multithreading support 
  * Added an option to enable/ disable the collection of Smart Event Lifecycle.
  * Made No of Threads , Log Level , Timeout , Pagesize for response configurable by user. 

* Version 2.5.0:
  * Compatibility with NAE v5.0
  * Added support of smart event lifecycle and user assignment data collection
  * Minor Bugfixes

* Version 2.4.0:
  * Compatibility with NAE v4.1
  * Added support of Remote User Authentication

* Version 2.3.0:
  * Added support of Splunk 8.x
  * Made Add-on Python2 and Python3 compatible

* Version 2.2.0:
  * Compatibility with NAE v4.0
  * Added support to collect all fabrics regardless of statuses(FINISHED, STOPPED, RUNNING)

* Version 2.1.0:
  * Added support of NAE v3.1

