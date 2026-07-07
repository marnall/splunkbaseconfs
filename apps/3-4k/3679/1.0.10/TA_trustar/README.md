# OVERVIEW

* The Technology Add-on integrates TruSTAR platform's IOCs and incidents with Splunk. With this Add-on security analysts utilize context and correlations from TruSTAR's intelligence to automate the process of finding connections between internal incidents.

* For dashboards with TruSTAR data, please install the TruSTAR App for Splunk available at https://splunkbase.splunk.com

# REQUIREMENTS

* Splunk version 7.0.x, 7.1.x and 7.2.x
* This application should be installed on Search Head, Indexer, and Forwarder.

# RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk configuration of Search Head, Indexer, and Forwarder.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app has been distributed in two parts.

    1) Add-on app, which listens for data from Trustar using REST API Calls.
    
    2) The main app for visualizing Trustar data.

* This App can be set up in two ways:

  1) __Standalone Mode__: Install the main app and Add-on app.

    * Here both the app resides on a single machine.
    * The main app uses the data collected by Add-on app and builds dashboard on it

   2) __Distributed Environment__: Install main app and Add-on app on search head, Only Add-on on forwarder system and need to create index manually on Indexer.
     
    * Here also both the apps reside on search head machine, but no need to configure Add-on on search head.
    * Only Add-on needs to be installed and configured on forwarder system.
    * On Indexer, Create index from menu Settings-> Indexes-> New, Give the name of index (for eg. trustar), which has been used in TA setup form on forwarder system.
    * Execute the following command on forwarder to forward the collected data to the indexer.
      $SPLUNK_HOME/bin/splunk add forward-server <indexer_ip_address>:9997
    * On Indexer machine, enable event listening on port 9997 (recommended by Splunk).
    * Main app on search head uses the received data and builds dashboards on it.

# INSTALLATION OF APP

* This app can be installed through UI using "Manage Apps" or from the command line using the following command:

    ```sh
    $SPLUNK_HOME/bin/splunk install app $PATH_TO_SPL/TA_trustar.spl/
    ```

* User can directly extract SPL file  into $SPLUNK_HOME/etc/apps/ folder.

# APPLICATION SETUP

* After installation:

1. Go to Settings->Data inputs->TruSTAR Configuration
2. Enter all required information

* Note: By default, all data is indexed to the main index. If you are using TruSTAR App for Splunk for visualization purpose and want to use a custom index then kindly update "trustar_get_index" macro in TruSTAR App for Splunk.

# TROUBLESHOOTING

* Environment variable SPLUNK_HOME must be set
* To troubleshoot TruSTAR application, check $SPLUNK_HOME/var/log/trustar/trustar_modinput.log file.

# SUPPORT

* Access questions and answers specific to TruSTAR App For Splunk at https://answers.splunk.com.
* Support Offered: Yes
* Support Email: splunkapp@trustar.co
* Please visit https://answers.splunk.com, and ask your question regarding TruSTAR Add-on for Splunk. Please tag your question with the correct App Tag, and your question will be attended to.

# SAVEDSEARCHES

* trustar_get_matched_reports
This saved search is used to get reports which matches with TruSTAR reports.

* Notable Events to TruSTAR
This saved search is used to send all the notable events to TruSTAR from Splunk ES

# CUSTOM COMMANDS

This application contains following custom command, which is used to upload reports.

* trustariocupload
This custom command is used to upload reports to TruSTAR platform.

# Splunk ES - Threat Intelligence 

To populate dashboards of Threat Intelligence in Splunk ES enable trustar_threat_intelligence scripted input present in TA_trustar.

* Steps to enable scripted inputs
1. Go to Settings->Data inputs->Script
2. Enable '$SPLUNK_HOME/etc/apps/TA_trustar/bin/trustar_threat_intelligence.py' script

Copyright (C) TruSTAR Technology 2017.