Checkpoint Dome9 App for Splunk
===============================

OVERVIEW
--------
The Checkpoint Dome9 App for Splunk is used to present the Checkpoint Dome9 findings data into Splunk. There are two dashboards named Alerts and Insights. User can perform exclude action from Alerts dashboard. Insights dashboard is used for visualization of findings.

* Author - Checkpoint Dome9
* Version - 1.0.0
* Build - 1
* Creates Index - False
* Compatible with:
   * Splunk Enterprise version: 7.3, 7.2 and 7.1
   * OS: Platform independent
   * Browser: Google Chrome, Mozilla Firefox, Safari



TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
------------------------------------------
This app can be set up in two ways: 
  1. Standalone Mode: 
     * Install the `Checkpoint Dome9 App for Splunk`.
     * Create HEC input to collect Dome9 Alerts data. See `CONFIGURATION > Data Collection` section for details.
     * Configure the App. See `CONFIGURATION > App Setup` section for details.
  2. Distributed Mode: 
     * Install the `Checkpoint Dome9 App for Splunk` on the search head. (Required for dashboards and search time extractions for CIM mapping.)
     * Configure the App. See `CONFIGURATION > App Setup` section for details.
     * Install the `Checkpoint Dome9 App for Splunk` on the heavy forwarder. (Required for timestamp extractions).
     * Create HEC input to collect Dome9 Alerts data. See `CONFIGURATION > Data Collection` section for details.
     * App setup is not required on the forwarder.
     * Note: Universal forwarder is not supported.



INSTALLATION
------------
Follow the below-listed steps to install an Add-on from the bundle:

* Download the App package.
* From the UI navigate to `Apps > Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.



CONFIGURATION
-------------

### Data Collection ###
For data collection we need to create one HEC input in the Splunk. Follow below steps to configure HEC input in Splunk.
* Go to `Settings > Data inputs > HTTP Event Collector`.
* Click on `Global Settings`.
* Enable `All Tokens`, if not already enabled.
* Click on `Save`.
* Click on `New Token`.
* Follow through the wizard to create a new HEC token.
  * Give name for the token.
  * Click on `Next`.
  * For `Source type`, use `Select` and from dropdown choose `checkpoint:dome9:alerts`. (The sourcetype might not be listed if you have not installed the App)
  * For `App context`, select `Checkpoint Dome9 App for Splunk`.
  * For `Index`, you can select any existing index or you can create any custom index. Follow https://docs.splunk.com/Documentation/Splunk/7.3.2/Indexer/Setupmultipleindexes for details. Make sure that you if the setup is in the distributed environment then the index needs to be created on Indexers from cluster master and need to be pushed to all the indexer.
  * Click on `Next` and `Submit`.
* Copy the `Token Value`.

To setup Alerts forwarding from Dome9 to Splunk user needs to follow below steps on Dome9 server.
* Login to Dome9 server (https://secure.dome9.com/v2/login).
* Go to `Compliance & Governance > Notification`.
* Click on `Add Notification`.
* Follow through the page to fill all the required information.
  * Give a name and a description to the notification.
  * In `Immediate Notification`, select `Send to HTTP Endpoint`.
  * Enter `https://<splunk_ip_or_host>:<HEC-port(default-9029)>/services/collector/raw` in `Endpoint URL`.
  * Set `Authentication Type` to `Basic`.
  * Add `x` in Username and `<HEC token>` in Password.
  * Select `JSON - Full entity` checkbox.
  * Click on `Save`.
* Select the policies from which alerts need to be forwarded to Splunk.
  * Go to `Compliance & Governance > Policies`.
  * Click on `Edit Notifications` button in front of the policy for which you want to send alerts.
  * Select the newly created notification and click on `Save`.
  * The Dome9 will automatically send the alerts to Splunk after this steps.
  * If you want to manually send all the Alerts to Splunk for the first time then you can follow below steps.
    * Click on `Send All Alerts` button in front of the Policy.
    * Select `Webhook` from `Notification Type`.
    * Select the created notification from `Notifications` list.
    * Click on `Send`.


### Macro Definition Change ###
Macro definition change is required to improve the dashboard performance. Follow below steps to change the macro definition.
* Go to `Settings > Advanced search > Search macros`.
* Change `App` to `Checkpoint Dome9 App for Splunk`.
* Search for `checkpoint_dome9_data` and click on it.
* Change value in the definition section from `index=*` to `index=<custom-index>`. The `custom-index` is the index which you have selected in `Data Collection` section while creating HEC token.
* Keep `sourcetype="checkpoint:dome9:alerts"` as it is.
* Final value should look something like: `index=main sourcetype="checkpoint:dome9:alerts"`.


### App Setup ###
* From the Splunk UI navigate to `Apps > Manage Apps > Checkpoint Dome9 App for Splunk > Set up`.

* Enter the following details of your Dome9 server and save the configuration.
  * API Key: Checkpoint Dome9 API Key
  * Secret Key (Password): Checkpoint Dome9 API Secret Key
  * Check the checkbox `Enable Proxy` if you want to use proxy server to connect to Checkpoint Dome9 server. And add below proxy details.
    * Proxy Scheme: Provide proxy protocol (http/https/socks4/socks5)
    * IP / Hostname: IP address or hostname of proxy instance.
    * Port: Port used to connect to proxy instance.
    * Require Authentication for Proxy: Check this option if your proxy configuration requires authentication.
    * Username: Provide proxy username
    * Password: Provide proxy password

* Note: If you uncheck `Configure Dome9 API Key & Token` checkbox and click on `Save`, you would not be able to use "Exclude" functionality in the `Alerts` dashboard.

* By default, SSL Verification will be true. If you don't want to verify your SSL certificate, follow steps:
  * Go to `$SPLUNK_HOME$/etc/apps/checkpoint_dome9_app_for_splunk/local`.
  * Open `checkpoint_dome9.conf` file and add/update below stanza.
  ```
  [connection_params]
  ssl_verify = false
  ```
  * Save the file and restart the Splunk.

* Checkpoint Dome9 App is configured and ready to be used.


### Adding SSL Certificate ###
If you have used SSL certificate for your domain, you need to add certificate into Splunk. Follow below-listed steps to do the same:
* Go to `$SPLUNK_HOME$/etc/apps/checkpoint_dome9_app_for_splunk/bin/lib/certifi`.
* Open cacert.pem file and add your custom certificate details at the end of the file.
* Save the file and restart the Splunk.

Note: If the vendor has published the SSL certificate publicly, no need to add that manually.


UNINSTALL APP
-------------
To uninstall app, user can follow below steps:
* SSH to the Splunk instance
* Go to folder apps($SPLUNK_HOME/etc/apps)
* Remove the checkpoint_dome9_app_for_splunk folder from apps directory
* Restart Splunk

KNOWN LIMITATION
----------------
* Disable exclude button after taking the exclude action will work for specific findingKey. It will not disable each button of all row with same Rule Name or Rule ID.
* If someone has already removed exclusion or added new exclusion from Dome9 side, it will not reflect on Splunk side.


RELEASE NOTES
-------------
Version 1.0.0
* Created App with two dashboards, Insights and Alerts.
* Added transformation for timestamp extraction and CIM mapping with Alerts data-modal.
* Added setup page to configure API Key and Secret Key for Dome9 server to take actions like "Open Alert in Dome9" and "Exclude" from Alerts dashboard.



OPEN SOURCE COMPONENTS AND LICENSES
------------------------------
* Some of the components included in Checkpoint Dome9 App for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.
     
    * pySocks version 1.7.1 https://pypi.org/project/PySocks/ (LICENSE https://github.com/Anorov/PySocks/blob/master/LICENSE)

    * certifi version 2019.09.11 https://pypi.python.org/pypi/certifi (LICENSE https://github.com/certifi/python-certifi/blob/master/LICENSE)

    * chardet version 3.0.4 https://pypi.python.org/pypi/chardet (LICENSE https://github.com/chardet/chardet/blob/master/LICENSE)
    
    * idna version 2.8 https://pypi.python.org/pypi/idna/2.8 (LICENSE https://github.com/kjd/idna/blob/master/LICENSE.rst)

    * requests version 2.22.0 http://docs.python-requests.org/en/master/ (LICENSE https://github.com/requests/requests/blob/master/LICENSE)

    * urllib3 version 1.25.6 https://pypi.python.org/pypi/urllib3/1.25.6 (LICENSE https://github.com/shazow/urllib3/blob/master/LICENSE.txt)



TROUBLESHOOTING
---------------
* Data collection issue
  * Check `Data Collection` guide from `CONFIGURATION` section to make sure HEC configuration is correct and configuration on Dome9 is good.
  * Verify the data via searching the data with `index=<your-selected-index-during-configuration>`.

* Data gets truncated in the events or Timestamp extraction or Field extraction issue
  * Make sure the App is properly installed on Heavy forwarder and Search head.

* Dashboards are not populating
  1. Look for the index in which we are indexing the data. If the data is not there in the index then check `Data collection issue` or else go through second point.
  2. Make sure the index is specified in the `checkpoint_dome9_data` macro. Check `Macro Definition Change` guide from `CONFIGURATION` section for more details.

* Alerts dashboard actions are not working
  * Error: API Key and Secret Key are not configured correctly. Please go to setup page and configure it to use Exclude functionality.
    * The issue is because the API Key and Secret Key are not configured. Follow `App Setup` guide from `CONFIGURATION` section to setup the API Key and Secret Key.
  * If you found any of the following errors, that could be because of API Key, Secret Key or Proxy details are not configured properly. Please follow `App Setup` guide from `CONFIGURATION` section to update those.
    * Proxy Authentication Failed. Please check your proxy configurations.
    * Authentication error while calling API, please recheck the API Key and Secret Key.
  * Make sure Javascript is enabled in the browser. Otherwise the Dashboard will not work as expected.



SUPPORT
-------
* Contact - #CheckpointDome9
  * International: +44-114 478 2845
  * US: +1 (888) 361-5030
* License Agreement - https://secure.dome9.com/v2/terms-and-conditions
* Copyright - 1994-2019 Check Point Software Technologies Ltd.
