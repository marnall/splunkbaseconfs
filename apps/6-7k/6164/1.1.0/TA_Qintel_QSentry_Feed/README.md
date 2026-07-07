# Qintel QSentry Feed Add-on for Splunk #

# OVERVIEW #
QSentry is a consumable feed of anonymization and threat actor IP addresses sourced from the Deep and DarkWeb and Qintel’s proprietary research. The IPs in the feed are associated with infrastructure actively utilized or abused by cyber criminals, including VPN/Proxy services and IP addresses linked to the malicious infrastructure of criminal and nation-state actors. With this integration, users can fetch a daily list of newly compiled indicators from QSentry’s collections.

The Qintel QSentry Feed Add-on for Splunk allows you to ingest the Qintel QSentry feed into a key value store in Splunk so that your logs data can be enriched automatically or at search time.

 - Author: Qintel
 - Version: 1.1.0
 - Creates Index: False
 - Has index-time operation: True
 - Implements summarization: False
 - Prerequisites: Qsentry API token
 - Conflicts: Do not install Qintel QSentry Feed Add-on for Splunk and Qintel QSentry Add-on for Splunk together

# COMPATIBILITY MATRIX #
 - Splunk Enterprise version: 8.x, 9.0, 9.1, 9.2
 - OS: Platform independent
 - Vendor Products: Qintel QSentry Feed

# RELEASE NOTES (Version 1.1.0) #
- Fixed JQuery 3.5 compatability
- Upgraded underlying splunk libraries (splunklib, splunktalib, solnlib, splunktaucclib)
- Updates Qintel helper to version 1.0.2 to support new default API URL
- Update processes to support larger feeds

# RELEASE NOTES (Version 1.0.0) #
- Integrates new Qintel helper file to pull the Qsentry Feed into a local KV store
- creates `qsentryfeed` custom search command 
- allows configuration of how many days of feeds to pull and how many days to keep data before it's purged

# INSTALLATION #
Follow the below-listed steps to install an app from the bundle:

 - Download the App package.
 - From the UI navigate to Apps > Manage Apps.
 - In the top right corner select Install app from file.
 - Select Choose File and select the App package.
 - Select Upload and follow the prompts.
 - Restart the Splunk to complete the installation.

# CONFIGURATION #
The app can be configured in the following way:

 - From the Splunk UI navigate to `Apps > Qintel QSentry Feed Add-on for Splunk > Configuration`.
 - Click on Qintel QSentry Feed Configuration and enter your QSentry Feed API Key.
 - Enter a value for how many days of the feed you want to pull (default is 1 day).
   - *Note: increasing this value will increase RAM usage for the initial pull, dailys feeds will be cached afterwards.*
 - Enter a value for the maximum feed age, the number of days to keep the data before it's purged (default is 2 days).
 - Optionally, enter a QSentry API URL if you want to use a non-default URL.
 - Click on Save button.
 - The app is now configured and is able to pull the data feed from QSentry into your local KV store.

Logging

 - User can configure the log level by navigating to `Apps > Qintel QSentry Feed Add-on for Splunk > Configuration` and selecting Logging.


# Pulling the QSentry Feed #

This TA installs a saved search that runs on a cron schedule `0 */6 * * *` to pull the configured feed from QSentry into your local KV store.
 - User can pull the feed manually by navigating to `Apps > Qintel QSentry Feed Add-on for Splunk > Reports` and finding `qintel_update_feed` and clicking `Open in Search` 


# Caching #
This add-on pulls the configured QSentry data feed into a local key value store.

You can view the contents in the following way:
 - From the Splunk UI navigate to `Apps > Qintel QSentry Feed Add-on for Splunk > Datasets`.
 - Click on `qintel_qsentry_feed`.

## Cleaning the Cache ##
This TA installs a saved search that runs on a cron schedule `30 */3 * * *` to purge the feed from QSentry into your local KV store based on your configuration settings.

You can clean the feed manually in the following way:
- From the Splunk UI navigate to `Apps > Qintel QSentry Feed Add-on for Splunk > Reports` and find `qintel_clean_feed` and click `Open in Search` 


# CUSTOM COMMANDS #
The following command is included as a part of the add-on:

 - qsentryfeed
    - Search format: `QUERY | qsentryfeed ip_field=<ip_field>"` 
    - Purpose: Retrieves context information for all of the given IP addresses from the QSentry Feed.


# Dashboard and Auto-Enrichment #

This TA does not include dashboards. 

You need to follow these steps to add enrichment tags to events, and then install the `Qintel Dashboards App for Splunk`

1. From the Splunk Web home screen, select the "Settings" dropdown from the top menu bar.
2. Select "Event Types" from the dropdown
3. Click the "New Event Type" button to add a new event type
4. Configure the following:
    - Destination App: TA_Qintel_QSentry_Feed
    - Name: descriptive name of the event type
    - Search String: search string specifying the events to be enriched (e.g. "sourcetype=auth" or "host=10.1.1.1")
    - Tag(s): 'qintel', 'network'
5. Click "Save"

**Note: it is important that the Qintel QSentry Feed Add-on for Splunk be configured as the "Destination App". If this is not possible, ensure the sharing permissions on the event type are such that the Qintel QSentry Feed Add-on for Splunk can access it ("Everyone/Read" from "All Apps" is sufficient)**


## Returns

Splunk events are enriched with the following fields that are returned from the Qintel QSentry Feed:
```
qintel_descriptions
qintel_tags
```

# UNINSTALL APP #
To uninstall app, user can follow below steps: 

 - SSH to the Splunk instance 
 - Go to folder apps($SPLUNK_HOME/etc/apps) 
 - Remove the TA_Qintel_QSentry_Feed* folder from apps directory 
 - Restart Splunk


# Support
 - Email: integrations-support@qintel.com


# COPYRIGHT #

 - Copyright (c) 2009-2024 Qintel, LLC
