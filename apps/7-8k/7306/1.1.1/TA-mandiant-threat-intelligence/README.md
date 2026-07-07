## Overview

Enrich your data with Threat Intelligence from Mandiant. The modular input included in this application collects context-rich indicators of compromise from the Mandiant API and ingests them locally into a Splunk index where they can be queried and used to provide additional context to security telemetry through Splunk lookups.

## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox
* OS: Platform Independent
* Splunk Enterprise version: 10.4.x, 10.2.x, 10.0.x, 9.4.x and 9.3.x
* Supported Splunk Deployment: Splunk Standalone and Distributed Deployment

## RELEASE NOTES

### Version 1.1.1
* Bumped the minimum required Python version to 3.13 as per Splunk standards.

### Version 1.1.0
* Migrated TA from AOB to UCC version 6.0.1.

## Installation guidelines

### Standalone Splunk Environment

Install the application via Splunkbase or upload the `.spl` file through the Splunk app installation UI.

### Distributed Splunk Environment

Install the application on both the Splunk Heavy Forwarder and Search Head for full functionality.

## Setup

This application requires setup, the Indicators dashboard will not display any results until setup is successfully completed and data collection has run at least once.

### Proxy Settings (Optional)

If a Proxy Server is required for internet access from the Splunk server, configure the application's Proxy settings.

1. While logged into the Splunk Web UI as an administrator, open the Mandiant Threat Intelligence application
2. Open the Settings | Configuration page from the navigation bar
3. On the Proxy tab select the Enable checkbox
4. Add the IP address or hostname of the proxy server without the protocol prefix in the Host textbox
5. Add the port to use for proxy connections in the Port textbox
6. If the Proxy Server requires authentication enter the username and password 
7. Click Save

**Note on Distributed Environments:** Complete this step on the Splunk Heavy Forwarder

### Add an Account

1. While logged into the Splunk Web UI as an administrator, open the Mandiant Threat Intelligence application
2. Open the Settings | Configuration page from the navigation bar
3. On the Account tab click the Add button
4. Enter the Mandiant Key ID and Key Secret (see https://docs.mandiant.com/home/mati-threat-intelligence-api-v4#tag/Getting-Started to learn how to get Mandiant API Keys)
5. Click Save

On save, API connectivity and API authentication is verified.

**Note on Distributed Environments:** Complete this step on the Splunk Heavy Forwarder

### Add an Indicator Input

1. While logged into the Splunk Web UI as an administrator, open the Mandiant Threat Intelligence application
2. Open the Settings | Inputs page from the navigation bar
3. Click Create New Input
4. Add a name for the Input in the Name textbox
5. Define an Interval for the Input to wait between data collection runs
6. Select the Index to use for ingested indicators
7. Select the Account created in the previous setup
8. Set the Indicator Time Window value. This setting is used to calculate a start date filter based on an indicators last seen date for the first data collection run
9. Optionally select to Include Open Source indicators. By default the input will only collect indicators sourced by Mandiant, optionally include indicators from open source sources. Note, this will increase the volume of indicators ingested into the Splunk environment
10. Click Save

On save data collection will start. 

**Note on Distributed Environments:** Complete this step on the Splunk Heavy Forwarder

### Viewing Indicator Data

Follow these steps to set the `mandiant_indicator_index` macro value,

1. While logged into the Splunk Web UI as an administrator, open the Mandiant Threat Intelligence application
2. Open the Settings | Configuration page from the navigation bar
3. Click the Indicator Settings tab
4. Set the value of the Indicator Index textbox
5. Click Save

**Note on Distributed Environments:** Complete this step on the Splunk Search Head

To get started searching for indicators, use the query: 
```index=`mandiant_indicator_index` sourcetype="mandiant:indicators"``` 
where `<index>` is the name of the index that Indicators are being ingested in to.

**Additional Notes:**
* An indicator's last seen date time is used as the Splunk `_time` field.
* As indicators are collected from Mandiant and ingested into Splunk the Indicators dashboard will start to show results. 


## Lookups

The application includes a lookup table definition for Mandiant Indicators, a Splunk Saved Search to populate the lookup from indicators ingested into a Splunk index, and Splunk Macros to customize the Saved Search.

### Customize Indicator Settings

Custom Splunk Macros are used to customize which indexed indicators get included in the Mandiant Indicator Lookup.

1. While logged into the Splunk Web UI as an administrator, open the Mandiant Threat Intelligence application
2. Open the Settings | Configuration page from the navigation bar
3. Click the Indicator Settings tab
4. Select the Enable Lookup checkbox
5. Set the minimum Threat Score of indicators included in the lookup
6. Set the age of indicators included in the lookup based on an indicators last seen value
7. Click Save

**Note on Distributed Environments:** Complete this step on the Splunk Search Head

### Enable the Mandiant Indicator Lookup Saved Search

1. While logged into the Splunk Web UI as an administrator, open the Settings | Searches, Reports, and Alerts page
2. Set the App to Mandiant Threat Intelligence
3. Set the Owner to All or Nobody
4. From the Edit dropdown of the Mandiant Indicator Lookup row, select Enable
5. Optionally edit the schedule of the Saved Search to control how frequently the lookup table will be refreshed

**Note on Distributed Environments:** Complete this step on the Splunk Search Head

### Using the Mandiant Indicator Lookup

Enrich security events with context from Mandiant by including this to your queries:

`<SPLUNK QUERY> | lookup mandiant_indicator_lookup value AS <FIELD_NAME>`

Where `<SPLUNK QUERY>` is a valid Splunk query that returns results and `<FIELD_NAME>` is the name of a field in your results containing the indicator value to lookup in the Mandiant Indicator Lookup. This must be either an IP Address (v4), domain name, url, or a file hash (Md5, SHA1, or SHA256)

**Note on Distributed Environments:** Complete this step on the Splunk Search Head

## SAVEDSEARCH

* `Mandiant Indicator Lookup` Populate the mandiant_indicator_lookup KV Store with Mandiant indicators

## UPGRADE

### General Upgrade Steps

* Go to Apps > Manage Apps and click on the "Install app from file".
* Click on "Choose File" and select the `TA-mandiant-threat-intelligence` installation file.
* Check the Upgrade app checkbox and click on Upload.
* Restart the Splunk instance.

Note :

* Before upgrade disable all the enabled inputs from the UI Inputs Page. Once the upgrade is successful, user can re-enable the inputs from the UI Inputs Page.

## TROUBLESHOOTING
### If Data is not getting collected in Splunk -
* Check below log files.
    * `$SPLUNK_HOME/var/log/splunk/splunkd.log`
    * `$SPLUNK_HOME/var/log/splunk/ta_mandiant_threat_intelligence_mati_indicators.log`
* User can search for ERROR logs in the Splunk using following query.
    * `index="_internal" source=*ta_mandiant*.log ERROR`
    * `index="_internal" sourcetype=*ta_mandiant* ERROR`
* Check that you have selected the correct sourcetype.
* Make sure that Secret Key which you have entered while configuring the Account is not expired.
* Make sure that Splunk restarts or disabling of input action should not be performed while input (data collection) is running.

### If any field is not getting extracted -
* By default, Splunk extracts maximum 100 fields at a Search time. Refer Splunk doc [here](https://docs.splunk.com/Documentation/Splunk/latest/Admin/Limitsconf#.5Bkv.5D). To extract all the fields, following change needs to be done -
    * Create limits.conf in local folder of your TA ($SPLUNK_HOME/etc/apps/TA-mandiant-threat-intelligence/local) with below content.
    ```
    [kv]
    limit=0
    ```
    * Restart Splunk.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

## UNINSTALL ADD-ON
* To uninstall the add-on, the user can follow the below steps.
    * Remove $SPLUNK_HOME/etc/apps/TA-mandiant-threat-intelligence
    * Remove $SPLUNK_HOME/var/log/Splunk/ta_mandiant_threat_intelligence_mati_indicators.log*.
    * To reflect the cleanup changes in UI, Restart Splunk Enterprise instance.

## Contact

* Email: customersupport@mandiant.com

**Copyright (c) 2026 Mandiant. All rights reserved.**
# Binary File Declaration
/usr/local/google/home/adamhlevy/splunk/splunk/var/data/tabuilder/package/TA-mandiant-threat-intelligence/bin/ta_mandiant_threat_intelligence/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
