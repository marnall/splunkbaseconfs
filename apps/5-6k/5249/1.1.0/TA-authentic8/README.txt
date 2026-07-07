Authentic8 Add-on for Splunk (TA-authentic8)
=============================================

Version: 1.1.0
Built with Splunk Add-on Builder.


Supported Versions
------------------

Splunk Enterprise: 9.x, 10.x

Python: 3.7+


Installation
------------

1. In Splunk Web, go to Apps > Manage Apps > Install app from file.

2. Select the TA-authentic8 package (.tar.gz or .spl), check "Upgrade app" if replacing an existing version, then click Upload.

3. Restart Splunk when prompted.

4. (Optional) Install the Splunk Common Information Model (CIM) app from https://splunkbase.splunk.com/app/1621 for field normalization.


Configuration
-------------

### Inputs

Go to the Authentic8 app and click the Inputs tab.
Click "Create New Input" and fill in the following fields:

  Name (required)              Unique name for this input.
  Interval (required)          Collection interval in seconds (e.g. 300 = 5 min).
  Index (required)             Splunk index to store the data.
  Authentic8 API URL (required)  API endpoint. Default: https://extapi.authentic8.com/api/
  Auth Token (required)        API token for authentication.
  Organization Name (required) Organization to collect logs for.
  Log Type                     Comma-separated list of log types, or "all" (default).

Multiple inputs can be created for different organizations or log type combinations.
Each input tracks its own collection state independently.

### Private Keys

For encrypted (ENC) log decryption, go to the Private Keys Setup tab.
Enter the key name and corresponding private key, then click Add.

### Proxy

Go to Configuration > Proxy to configure HTTP/SOCKS proxy settings.

### Logging

Go to Configuration > Logging to set the log level.
Available levels: DEBUG, INFO (default), WARNING, ERROR, CRITICAL.

Addon logs are written to:
  $SPLUNK_HOME/var/log/splunk/ta_authentic8_authentic8.log


Upgrading from 1.0.x
--------------------

When upgrading from version 1.0.x, existing checkpoint data is automatically migrated to the new input-specific format on the first run.
No manual action is required.

The list of supported log types is now updated automatically from the API once per day.
New log types added by Authentic8 will be picked up without requiring an addon upgrade.


Search
------

To view collected data, go to the Search tab and query:

  index=<your_index> sourcetype="Authentic8"

Use "All Time" as the time range if data was recently ingested for the first time.
