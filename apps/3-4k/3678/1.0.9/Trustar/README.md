# OVERVIEW
 
The TruSTAR App for Splunk allows users to utilize the context of the TruSTAR platform's IOCs and incidents within their Splunk workflow. TruSTAR arms security teams with the highest signal intelligence from sources such as internal historical data, open and closed intelligence feeds and anonymized incident reports from TruSTAR's vetted community of enterprise members.

# REQUIREMENTS

* Splunk version 7.0.x, 7.1.x and 7.2.x
* This application should be installed on Search Head.

# RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk configuration of Search Head.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app has been distributed in two parts.

    1) Add-on app, which listens for data from Trustar using REST API Calls.
    
    2) The main app for visualizing Trustar data.

* This App can be set up in two ways:

  1) __Standalone Mode__: Install the main app and Add-on app.

  * Here both the app resides on a single machine.
  * The main app uses the data collected by Add-on app and builds dashboard on it

  2) __Distributed Environment__: Install the main app and Add-on app on search head. Add-on app on forwarder and Indexer.

  * Configure Add-on app on forwarder.
  * The main app on search head uses the received data and builds dashboards on it.

# INSTALLATION IN SPLUNK CLOUD

* Same as on-premise setup.

# INSTALLATION OF APP

* This app can be installed through UI using "Manage Apps" or from the command line using the following command:
    ```sh
    $SPLUNK_HOME/bin/splunk install app $PATH_TO_SPL/Trustar.spl/
    ```
* User can directly extract SPL file  into $SPLUNK_HOME/etc/apps/ folder.

# SUPPORT

* Access questions and answers specific to TruSTAR App for Splunk at https://answers.splunk.com.
* Support Offered: Yes
* Support Email: splunkapp@trustar.co
* Please visit https://answers.splunk.com, and ask your question regarding TruSTAR App for Splunk. Please tag your question with the correct App Tag, and your question will be attended to.

# SAVEDSEARCHES

This application contains following thirty saved searches, which are used in the dashboard.

* get_enclaves
This saved search is used to fetch enclaves to populate Enclaves dropdown.

* Trustar_All_Indicators_Cumulative
This saved search is used to populate "trustar_all_indicators_cumulative_lookup" lookup.

* TruStar_Mark_False_Positive
This saved search is used to populate "trustar_false_positive_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_MD5
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_SHA256
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_SOFTWARE
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_SHA1
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_URL
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_REGISTRY_KEY
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_MALWARE
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_EMAIL_ADDRESS
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_IP
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_CVE
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_BITCOIN_ADDRESS
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_CIDR_BLOCK
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_All_Matching_Indicators_Cumulative_For_Type_PHONE_NUMBER
This saved search is used to populate "trustar_matching_indicators_cumulative_lookup" lookup.

* Trustar_Reports_Indicators_Cumulative
This saved search is used to populate "trustar_all_reports_cumulative_lookup" lookup.

* Trustar_Match_Indicators_For_Type_MD5
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

* Trustar_Match_Indicators_For_Type_SHA256
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

* Trustar_Match_Indicators_For_Type_SOFTWARE
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

* Trustar_Match_Indicators_For_Type_SHA1
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

* Trustar_Match_Indicators_For_Type_URL
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

* Trustar_Match_Indicators_For_Type_REGISTRY_KEY
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

* Trustar_Match_Indicators_For_Type_MALWARE
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

* Trustar_Match_Indicators_For_Type_EMAIL_ADDRESS
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

* Trustar_Match_Indicators_For_Type_IP
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

* Trustar_Match_Indicators_For_Type_CVE
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

* Trustar_Match_Indicators_For_Type_BITCOIN_ADDRESS
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

* Trustar_Match_Indicators_For_Type_CIDR_BLOCK
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

* Trustar_Match_Indicators_For_Type_PHONE_NUMBER
This saved search is used to populate "trustar_indicators_match_result_lookup" lookup.

# CUSTOM COMMANDS

This application contains following custom commands, which are used in the dashboard.

* match
This custom command is used in "Trustar_All_Matching_Indicators_Cumulative" saved search to get list of matching indicators with splunk raw events.

* addindicator
This custom command is used in "TruSTAR Indicators" dashboards to add whitelisted indicator to threat intelligence collections.

* removeindicator
This custom command is used in "TruSTAR Indicators" dashboards to remove whitelisted indicator from threat intelligence collections.

Copyright (C) TruSTAR Technology 2017.