# OVERVIEW

* The Technology Add-on for PureStorage FlashBlade is used to monitor customer’s PureStorage FlashBlade fleet within a Splunk environment.
* This Add-on uses splunk KV store for checkpoint mechanism.
* Author - PureStorage Inc
* Version - 1.0.2
* Supported Splunk versions are 7.0, 7.1, 7.2 and 7.3
* Supports FlashBlade REST API 1.5 and above (Purity Version 2.2.9 and above)

# RELEASE NOTES

  * Version - 1.0.1
    * Updated Logo.
  * Version - 1.0.2
    * Bug fixes

# REQUIREMENTS
* Splunk version 7.0.x, 7.1.x, 7.2.x or 7.3.x
* Appropriate API Token for collecting data from FlashBlade

# RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk configuration of Search Head, Indexer, and Forwarder.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app has been distributed in two parts.
1) Add-on app, which fetches the data from FlashBlade Rest API.
2) The main app for visualizing data.

* This App can be set up in two ways:

1) __Standalone Mode__:
  
* Install the main app and Add-on app.

    * Here both the app resides on a single machine.
    * The main app uses the data collected by Add-on app and builds dashboards on it

 2) __Distributed Environment__: 

* Search head
    * Install main app and Add-on both.
    * No need to configure Add-on here.

* Indexer
    * If you are using custom index define it here.

* Forwarder
    * Install and Configure Add-on.
    
# INSTALLATION IN SPLUNK CLOUD

* Same as on-premise setup.

# INSTALLATION OF APP

* This app can be installed through UI using "Manage Apps" or from the command line using the following command:

    ```sh
    $SPLUNK_HOME/bin/splunk install app $PATH_TO_SPL/TA-ps_flashblade.spl/
    ```

* User can directly extract SPL file  into $SPLUNK_HOME/etc/apps/ folder.

# APPLICATION SETUP

### After installation:

* Navigate to PureStorage FlashBlade Add-on, click on "Configuration" page, go to "Account" tab and then click "Add", fill in "Account Name", "Server Address" and "API Token"  then click add to add a FlashBlade .

* Navigate to PureStorage FlashBlade Add-on, click on "Configuration" page, go to "proxy" tab and fill in "Proxy Type", "Host", "Port" and "Credentials"  then tick enable and at last click save the proxy settings. *This is only to be done if proxy is needed* .

* Navigate to PureStorage FlashBlade Add-on, click on "Configuration" page, go to "logging" tab and select logging level from the drop down and click save .

* Navigate to PureStorage FlashBlade Add-on, click on create new input and fill the "Name", "Interval", "Index", "Global Account" and "Start Date" fields. All fields except "Start Date" are mandatory and if no value provided "Start Field" defaults to date of previous 7th Day.

* Note:- User with Splunk admin role can configure and access the add-on configuration. If user is not able to view the add-on configuration page then please provide the admin role to the user from Settings -> Access controls -> Users -> Select a User -> Provide admin role -> Save.

# Splunk IT Service Intelligence Compatibility

The PureStorage FlashBlade Add-on is compatible with Splunk IT Service Intelligence (ITSI) storage module.

Hence dashboards related to performance can be viewed on ITSI app as well.

# SAMPLE EVENT GENERATOR

The PureStorage FlashBlade Add-on, comes with sample data files, which can be used to generate sample data for testing. In order to generate sample data it requires SA-Eventgen application. The Add-on will generate sample data of rest API calls at an interval of 600 seconds. You can update this configuration from eventgen.conf file available under $SPLUNK_HOME/etc/apps/default/.

# Troubleshooting

* Environment variable SPLUNK_HOME must be set
* To troubleshoot PureStorage Flashblade mod-input check *$SPLUNK_HOME/var/log/splunk/ta_ps_flashblade_purestorage_flashblade.log* file.
* No sample events generated after installing SA-Eventgen. Check if you have enabled all samples by doing `disabled=false` in eventgen.conf and you have enabled eventgen inside settings -> data inputs from Splunk UI.


# SUPPORT

* Access questions and answers specific to PureStorage FlashBlade App at https://answers.splunk.com.
* Support Offered: yes
* Support Email: support@purestorage.com
* Please visit https://answers.splunk.com, and ask your question regarding PureStorage FlashBlade App. Please tag your question with the correct App Tag, and your question will be attended to.

### Copyright (c) 2019 Pure Storage, Inc. All Rights Reserved