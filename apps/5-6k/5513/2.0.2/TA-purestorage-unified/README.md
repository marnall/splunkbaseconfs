# OVERVIEW

* The Everpure Unified Add-on is used to collect logs, alerts, audits, and metrics from Everpure FlashBlade, FlashArray, and Pure1 into your Splunk environment.
* This Add-on uses the Splunk KV store for the checkpoint mechanism.
* Author - Everpure
* Version - 2.0.2
* Supported Splunk versions are 10.2.x, 10.1.x, 10.0.x, 9.4.x, 9.3.x
* Supported OS versions are CentOS and Windows
* Supported Browser versions are Chrome and Firefox
* Supports FlashBlade REST API 1.0 to 1.11, 2.2 and 2.8 (except 1.10)
* Supports FlashArray REST API 1.13 to 1.18 and 2.2(all endpoints) and 2.4(sessions endpoint) (FA/Purity Version 5.0.0 and above)
* Supports Pure1 REST API 1.latest


# RELEASE NOTES

  * Version - 2.0.2
    * Bug Fixes
        * Skip destroyed buckets in FlashBlade Bucket performance collection

  * Version - 2.0.1
    * Added support for Splunk 10.x
    * Migrated to Splunk add-on builder v4.5.0
    * Updated to Everpure branding
    * Bug Fixes
    
  * Version - 1.6.0
    * Renamed the index field in FlashBlade Alerts to alert_index.
  
  * Version - 1.5.0
    * Added support for 'array_total_load' metric.

  * Version - 1.4.0
    * Migrated to Splunk add-on builder v4.1.3

  * Version - 1.3.0
    * Added support for APIv2 for FlashArray and FlashBlade.
    * Enhanced checkpointing mechanism for sessions, alert and audit endpoints.
    * Migrated to Splunk add-on builder v4. (Supporting jQuery 3.5.0)
      * UI overhaul
      * Mitigated jQuery vulnerabilities
    * Removed support for python2.
    * Bugfixes
  
  * Version - 1.2.0
    * Provided support of Mirrored Write in FlashArray and Pure1 > Array (only for FlashArray).

  * Version - 1.1.0
    * Provided support of Pure1.
    * Added support for Batch configuration of Systems and Inputs.

  * Version - 1.0.0
    * Provided support of FlashArray and FlashBlade.

# REQUIREMENTS
* Splunk version 10.2.x, 10.1.x, 10.0.x, 9.4.x, 9.3.x
* Appropriate API Token for collecting data from FlashBlade and FlashArray or JWT token for collecting data from Pure1.

# RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk configuration of Search Head, Indexer, and Forwarder.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app has been distributed in two parts.
1) Add-on app, which fetches the data from FlashBlade and FlashArray Rest API.
2) The main app for visualizing data.

* This App can be set up in two ways:

1) __Standalone Mode__:
  
* Install the main app and Add-on app.

    * Both the main app and Add-on resides on a single machine.
    * The main app uses the data collected by the Add-on app and displays them on the prebuilt dashboards

 2) __Distributed Environment__: 

    * Search head
        * Install main app and Add-on both.
        * No need to configure Add-on here.

    * Indexer
        * If you want to use a custom index for this app define it here.
        * No need to install the Add-on here.

    * Heavy Forwarder
        * Install and Configure Add-on.
    
# INSTALLATION IN SPLUNK CLOUD

* Same as an on-premise setup.

# INSTALLATION OF APP

* This app can be installed through UI using "Manage Apps" or from the command line using the following command:

    ```sh
    $SPLUNK_HOME/bin/splunk install app $PATH_TO_SPL/TA-purestorage-unified.spl/
    ```

* User can directly extract SPL file into $SPLUNK_HOME/etc/apps/ folder.

# UPGRADATION OF APP

Follow the below steps to upgrade the App from Splunk Web UI

* Go to Apps > Manage Apps and click on the "Install app from file".
* Click on "Choose File" and select the TA-purestorage-unified installation file.
* Check the Upgrade app checkbox and click on Upload.
* Restart the Splunk instance.

# POST UPGRADATION STEPS
####  Upgrading the Add-on to v1.x.0 from 1.0.0

* If you want to disable SSL certificate validation, then follow the below steps:
    * Navigate to path: `$SPLUNK_HOME/TA-purestorage-unified/local/`. If folder `local` is not present at the location: `$SPLUNK_HOME/TA-purestorage-unified/`, create folder named `local` at the location.
    * Check for file: `ta_purestorage_unified_settings.conf` at location: `$SPLUNK_HOME/TA-purestorage-unified/local/`. If the file is not present, create the file `ta_purestorage_unified_settings.conf` at the location.
    * In file `$SPLUNK_HOME/TA-purestorage-unified/local/ta_purestorage_unified_settings.conf` add stanza `purestorage_additional_parameters` at the end of the file and set the value of `verify_ssl` variable to `False` as done below :
        ```
        [purestorage_additional_parameters]
        verify_ssl = False
        ```
    * Restart Splunk

# APPLICATION SETUP

### After installation:

* Navigate to Everpure Unified TA, click on "Configuration" page, go to "System" tab and then click "Add", choose "System Type", fill in "System Name", "Server Address" (without the https scheme) and "Authentication/JWT Token" then click the "Add" button.
    * If "System Type" is FlashBlade/FlashArray, provide API Token in the "Authentication/JWT Token" field.
    * If "System Type" is Pure1, provide JWT Token in the "Authentication/JWT Token" field.

        **Note:**

        * Please follow the "Creating your ID Token" section in the following documentation to generate the JWT token for the Pure1 system:https://blog.everpuredata.com/products/introducing-the-pure1-rest-api/. You need to provide the JWT token (not Access token) while configuring a Pure1 system in Splunk.
        * To get the API token, use the below CLI command that can be issued against FlashArray or FlashBlade.
            pureadmin list --api-token --expose
        * For System Type Pure1, only one input can be configured corresponding to one Pure1 System. Trying to configure multiple inputs with same Pure1 System is not allowed.

* Navigate to Everpure Unified TA, click on the "Configuration" page, go to the "proxy" tab, and fill in "Proxy Type", "Host", "Port", "Username" and "Password" then tick enable and at last click save the proxy settings. *This is only to be done if the proxy is needed*.

* Navigate to Everpure Unified TA, click on the "Configuration" page, go to the "logging" tab and select logging level from the drop-down and click save.

* Navigate to Everpure Unified TA, click on the "Inputs" page, click on "Create New Input" and fill in the "Name", "Interval", "Index", and "Start Date" fields and choose "Input Type" and "System" (All fields are mandatory). Once done click Add.
  * For input type "FlashArray" and "Flashblade" there is an optional checkbox to collect historical data for Alerts, Audits, Sessions and Performance space metrics. If checked, it will collect the data from the specified "Start Date".

**Note:**

* If you have already configured a FlashBlade or FlashArray Input, then configuring a Pure1 input associated with the same FlashBlade and FlashArray or vice versa would lead to duplicate data/events in Splunk and will increase Splunk data volume and license usage.
* The data for Pure1 > metrics/history endpoint will be collected for end_time as current_time - 1hr, because the data is updated with delay in Pure1 API, and Splunk data collection is completed before the delayed update is made available.
* If the Start Date configured by the user is greater than current_time - 1hr, data for the metrics/history endpoint will not be collected.
* There is an acknowledgement checkbox which warns the user to collect data not earlier than 7 days ago. If an earlier start date is provided, it might result in using up the limited storage capacity based on the Splunk license.

### Batch System/ Input Configuration:
You can use the Batch configuration functionality to create multiple Systems/Inputs configurations by uploading a CSV file with the required details.

* Navigate to Everpure Unified TA, click on **Configuration** page, go to **Batch Creation** tab.
* Select from `System Configuration` or `Input Configuration` and select the corresponding CSV file to upload. The table in the dashboard indicates the required headers and corresponding description for the selected Configuration Type in the CSV file to be uploaded.

    * For **System Configuration** following headers are required in CSV file :
        * **name**           : Unique name for the System
        * **system_type**   : System type of the system. It should be one of these values - flash_blade_account, flash_array_account or pure1
        * **server_address** : Server address of the system without scheme
        * **api_token**      : The API Token for FlashBlade/FlashArray, JWT token for Pure1
        * **Sample CSV file content for "System Configuration"**:
        ```
            name,system_type,server_address,api_token
            fa_acc,flash_array_account,flasharray.example.com,12345678-1234-1234-1234-12345678
            fb_acc,flash_blade_account,flashblade.example.com,12345678-1234-1234-1234-12345678
            pure1_acc,pure1,api.pure1.purestorage.com,12345678-1234-1234-1234-12345678
        ```
    
    * For **Input Configuration** following headers are required in CSV file :
        * **name**        : Unique name for the Input
        * **interval**    : Time interval of input in seconds. Minimum 3600 seconds for Input Type Pure1, else minimum 60 seconds.
        * **index**	      : Index in which to ingest data for the input
        * **input_type**  : Input type to collect data. It should be one of these values - flashblade, flasharray or pure1
        * **system**      : System name from the System configurations with which to collect data
        * **start_date**  : The date (UTC in 'YYYY-MM-DDTHH:mm:ssZ' format) from when to start collecting the data
        * **historical_data** : Checkbox to collect historical data for flasharray and flashblade. This flag is only applicable when collecting data from native FlashArray and FlashBlade APIs. Keep 1/true/yes to enable and 0/false/no to disable Historical data collection.
        
        * **Sample CSV file content for "Input Configuration"**:
        ```
            name,interval,index,input_type,system,start_date
            FA_Input1,144000,default,flash_array,FA1,2021-08-01T00:00:00Z
            FB_Input1,144000,default,flash_blade,FB1,2021-08-01T00:00:00Z
            Pure1_Input1,144000,default,pure1,FB1,Pure1_Acc,2021-08-01T00:00:00Z
        ```
        * **Sample CSV file content for "Input Configuration (with historical_data)"**:
        ```
            name,interval,index,input_type,system,start_date,historical_data
            FA_Input1,144000,default,flash_array,FA1,2021-08-01T00:00:00Z,0
            FB_Input1,144000,default,flash_blade,FB1,2021-08-01T00:00:00Z,1
        ```

* Now click the upload button and wait for the processing to be completed.
* If any validation failures or error occurs for a particular System/Input configuration while Batch creation, the Validation Failure/ Error messages with associated line number in CSV file will be displayed in the panel in Red color. In case of successful creation of all given configurations, Sucess message will be displayed to you in the panel.
* Navigate to Everpure Unified TA, click on **Configuration** page, go to **System**/**Input** tab . The Systems/Inputs created from Batch Creation would be visible here.

    **Note:** In case of the partial success of Batch Creation, The Validation Failure/Error messages corresponding to configurations with an associated line number in CSV file will be displayed in the panel in Red color, and Configurations that were successfully created will be visible in the **Configuration** page, **System**/**Input** tab.

# UNINSTALLATION of App

* (Optional) If you want to remove data from the Splunk database, you can use the below Splunk CLI clean command to remove indexed data from an app before deleting the app.
* $SPLUNK_HOME/bin/splunk clean eventdata -index <index_name>

* Delete the add-on and its logs. The add-on and its logs are typically located in the folder $SPLUNK_HOME/etc/apps/ and $SPLUNK_HOME/var/log/splunk respectively. For this you can run the following commands in the CLI:
    * Remove addon: $SPLUNK_HOME/bin/splunk remove app TA-purestorage-unified -auth <splunk username>:<splunk password> 
    * To Remove log files:
        * rm -rf $SPLUNK_HOME/var/log/splunk/purestorage_unified_ta*.log 
        * rm -rf $SPLUNK_HOME/var/log/splunk/ta_purestorage_unified_purestorage_unified_input.log

* Restart the Splunk platform. You can navigate to Settings -> Server controls and click the restart button in Splunk web UI or use the following Splunk CLI command to restart Splunk:
    * $SPLUNK_HOME/bin/splunk restart

# Troubleshooting

* Environment variable SPLUNK_HOME must be set
* To troubleshoot Everpure Unified Add-on check $SPLUNK_HOME/var/log/splunk/ta_purestorage_unified_purestorage_unified_input.log file or execute below query:
    * Query: index="_internal" source="*ta_purestorage_unified_purestorage_unified_input.log"
* SSL verification is enabled by default. 
   * To collect the data on on-prem instance using the self-signed SSL certificate. Please add valid certificate in `$SPLUNK_HOME/TA-purestorage-unified/bin/ta_purestorage_unified/aob_py2/certifi/cacert.pem` or `$SPLUNK_HOME/TA-purestorage-unified/bin/ta_purestorage_unified/aob_py3/certifi/cacert.pem`. Valid self-signed certificate should have `Common Name` field set as server address and `Valid To` field as expiry date of the certificate. 
   Note: For adding a certificate on the cloud instance, raise a Splunk support ticket.

   * Follow the steps mentioned in section: **POST UPGRADATION STEPS** > **Upgrading the Add-on to v1.1.0 from 1.0.0**, to disable the SSL verification entirely before configuring credentials or collecting data using REST endpoints. Please use it at your discretion as the suggested approach is to use the secured connection.
    * This will disable the SSL verification while configuring credentials or collecting data using REST endpoints.

# Known Issues:

* TA will fetch live data for native FlashArray. If the input is disabled for a given time, then data for that duration won't be collected so you may observe a gap for that duration in time charts.
* Mirrored write may not work for Pure1 if the configured FlashArrays return zero values for mirrored write fields.
* There could be a null value in the id field for Pure1 volumes, which may result in missing volumes metrics data.
* For FlashArray API v2 sessions endpoint, either store value of start_time if it's not null in the API response or stores the current time in the checkpoint.
* Data duplication may occur for session data because of null valued timestamps returned from the API endpoint.
* When using FlashArray supporting only APIv1, you will not be able to see values under the origin field since it's supported in APIv2 only.

# SUPPORT

* Access questions and answers specific to Everpure Unified App at https://answers.splunk.com.
* Support Offered: yes
* Support Email: splunk-app@everpuredata.com
* Please visit https://answers.splunk.com, and ask your question regarding Everpure Unified App. Please tag your question with the correct App Tag, and your question will be attended to.

### Copyright (c) 2025 Everpure. All Rights Reserved