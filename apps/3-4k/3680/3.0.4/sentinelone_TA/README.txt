-----------------------------------------
SentinelOne Technical Add-on for Splunk
 
The SentinelOne Technical Add-on for Splunk is provided "as is", and its use is solely at user’s own risk.
 
-----------------------------------------
 
RELEASE NOTES:
  * Version 3.0.4
  * The TA can now be configured through Splunk UI.
  * Inputs mechanism rewritten.
  * Added CIM mappings to support Splunk ES
  * Upgrades from SentinelOne TA versions below 3.0 are not supported.
 
-----------------------------------------
1) INTRODUCTION
 
The integration of Splunk and SentinelOne empowers organizations to combine the strengths of their
Splunk deployments to collect, monitor, analyze and visualize massive streams of machine data with
the deep visibility, detection, response, remediation and forensics capabilities of SentinelOne EPP.

The SentinelOne TA (Technology Add-on) for Splunk collects the data from the SentinelOne Management Server and configures CIM mappings to support Splunk ES.
 
-----------------------------------------
2) REQUIREMENTS
 
- Hardware Requirements:
  Refer to <a href="http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements">System Requirements</a> document
 
- Software Requirements:
  * SentinelOne version [ ??? ]
  * Splunk Enterprise v6.5+ or Splunk Cloud
 
- Splunk Downloads: https://www.splunk.com/en_us/download.html
 
- Limitations: Add-on installation with inputs on SHC is not supported
 
-----------------------------------------
3) INSTALLATION AND CONFIGURATION
 
INSTALLATION:
  NOTE: Upgrades from SentinelOne TA versions below 3.0 are not supported. 
      You should uninstall or disable pre-3.0 TA versions before installing 3.0+ version of the TA
  
  - Installing on stand-alone Splunk instance
  Refer to <a href="http://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall">Splunk Documentation</a> for instructions 
   
  - Installing SentinelOne TA in a distributed Splunk Enterprise deployment
  Install the TA on a non-clustered search head or a heavy forwarder with enabled Web UI.

  - If CIM models are required for Splunk ES and other purposes, please install Splunk Common Information Model (CIM) Add-on https://splunkbase.splunk.com/app/1621

  
  * Install SentinelOne TA using Splunk UI.
  * Restart Splunk.
 
CONFIGURATION:
  * Open SentinelOne TA app
  * Set macro `s1_index` to use the relevant index for SentinelOne events: Setting => Advanced Search => Search macros => Change the definition from index=* to index=<desired index>.
  * Optional: If proxy is required for connecting to SentinelOne Console Manager - navigate to Configuration -> Proxy tab and configure proxy before defining inputs.
  * Navigate to "Inputs" tab and click "Create New Input"
  * Fill in the fields
    - Name      Input name
    - Interval      SentinelOne API polling interval in seconds
    - Index     Destination index. Either select index name from a drop-down list or type index name. Make sure the index exists at your deployment's indexing tier before saving input configuration.
    - Subdomain     Sub-domain name [!!! instruction where to get it!!!]
    - SentinelOne Domain        SentinelOne Domain [!!! instruction where to get it!!!]. Non-secure HTTP connections are not supported. 
    - API Token     SentinelOne API token [!!! instruction where to get it!!!]
    - API Channels      API channels to query for events. Could be "Activities", "Agents", "Groups", "Policies", "Threats" or all.
    - Start Time for the events
                          Start Time in epoch time format with milliseconds (e.g. 1513883092000) or "now" to collect only new events
                          The TA will collect all available historical data if initial checkpoint value is 0 (zero)
    - API URL Path      URL Path to API endpoint to pull events from. [!!! instruction where to get it!!!] or use the default value.
    - API Version       API Version [!!! instruction where to get it!!!] or use the default value.
    - Verify Console Certificate
                          Uncheck to bypass HTTPS SSL verification (insecure)
  
-----------------------------------------
4) UPGRADE
      
NOTE: Upgrades from SentinelOne TA versions below 3.0 are not supported. 
    You should uninstall or disable pre-3.0 TA versions, then install the 3.0+ version of the TA
 
When upgrading from pre-3.0 TA versions:
  * Backup $SPLUNK_HOME/etc/apps/sentinelone_TA directory.
  * Shut down Splunk
  * Uninstall pre-3.0 TA version by deleting $SPLUNK_HOME/etc/apps/sentinelone_TA directory or disable
  * Install new app using Splunk UI or CLI.
  * Restart Splunk
 
Upgrading 3.0+ TA versions
  * Install a new version of the TA
  * Restart Splunk
 
-----------------------------------------
5) TROUBLESHOOTING
 
* Check the SplunkWeb for any displayed messages: see the Messages menu to the left of Settings in the Splunk menu bar.
* Search sentinelone_ta_sentinelone_api.log for non-INFO messages::
            index=_internal sourcetype="sentineloneta:log" NOT "INFO"
* To control TA log level - Open SentinelOne TA app => Configuration => Logging and set desired Log Level
* Search internal Splunk logs for Errors:
            index=_internal sourcetype=splunkd
 
-----------------------------------------
 
6) Data Knowledge objects
 
Macros
  * s1_index - set index for all saved searches
  
Saved Searches
  * Agents List Lookup - populates agents_list lookup with SentinelOne agents details
  
Lookups
  * activities_list - Points to activities_list.csv lookup file in $SPLUNK_HOME/sentinelone_TA/lookups directory.
                      Used to convert numerical activity type to its description
  * mitigation_status - Points to activities_list.csv lookup file in $SPLUNK_HOME/sentinelone_TA/lookups directory.
                      Used to convert numerical mitigation status to its description
                      
  * agents_list - Points to agents_list.csv lookup file in $SPLUNK_HOME/sentinelone_TA/lookups directory.
                      Used for CIM mapping lookups  
-----------------------------------------
7) SUPPORT
 
SentinelOne Support:
support@sentinelone.com
 
To expedite handling of your email please furnish the following information:
 
* Splunk App version (at the top of this file or in app.conf)
* Splunk version
* OS and version
* Company name
* Description:
   E.g. feature, and how to invoke it e.g. the menu items clicked to arrive at a dashboard);
   E.g. bug, and how to reproduce the issue and describe the expected behavior versus the actual
   (suspected erroneous) behavior
* Supporting information:
   screenshot(s), log file(s), configuration files from $SPLUNK_HOME/etc/apps/sentinelone_TA/local directory.
 
-----------------------------------------
8) LICENSE
 
<a href="https://sentinelone.com/terms-of-service/">SentinelOne Terms of Service</a>
 
-----------------------------------------
9) CREDITS
 
SentinelOne TA was created using Splunk Add-on Builder App. <a href="http://docs.splunk.com/Documentation/AddonBuilder/2.2.0/UserGuide/Thirdpartysoftwarecredits">Third-part software credits</a>
 
[!!! Any other relevant credits !!!]

