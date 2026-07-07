# Qintel QSentry Add-on for Splunk #

# OVERVIEW #
QSentry is Qintel’s proprietary anonymization detection service that sources data directly from the Deep and DarkWeb.  Queries against the service helps measure the likelihood that a user is masking their identity.

The Qintel QSentry Add-on for Splunk allows you to perform real time queries of QSentry to enrich your log data automatically or at search time.

 - Author: Qintel
 - Version: 1.1.0
 - Creates Index: False
 - Has index-time operation: True
 - Implements summarization: False
 - Prerequisites: QSentry API token
 - Conflicts: Do not install Qintel QSentry Feed Add-on for Splunk and Qintel QSentry Add-on for Splunk together


# COMPATIBILITY MATRIX #
 - Splunk Enterprise version: 8.x, 9.0, 9.1, 9.2
 - OS: Platform independent
 - Vendor Products: Qintel QSentry

# RELEASE NOTES (Version 1.1.0) #
- Fixed JQuery 3.5 compatability
- Upgraded underlying splunk libraries and dependencies (splunklib, splunktalib, solnlib, splunktaucclib)

# RELEASE NOTES (Version 1.0.0) #
- Integrates new Qintel helper file to query QSentry and temporarily cache search results
- creates `qsentry` custom search command 

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

 - From the Splunk UI navigate to `Apps > Qintel QSentry Add-on for Splunk > Configuration`.
 - Click on Qintel QSentry Configuration and enter your QSentry API Key.
 - Enter a value for how many days of the feed you want to pull (default is 1 day).
 - Enter a value for the maximum feed age, the number of days to keep the data before it's purged (default is 2 days).
 - Optionally, enter a QSentry API URL if you want to use a non-default URL.
 - Click on Save button.
 - The app is now configured and is able to pull the data feed from QSentry into your local KV store.

Logging

 - User can configure the log level by navigating to `Apps > Qintel QSentry Add-on for Splunk > Configuration` and selecting Logging.
 

# Caching #
This add-on temporarily stores QSentry search data results into a local key value store.

You can view the contents in the following way:
 - From the Splunk UI navigate to `Apps > Qintel QSentry Add-on for Splunk > Datasets`.
 - Click on `qintel_qsentry_cache`.

## Cleaning the Cache ##
This add-on installs a saved search that runs every 5 minutes on a cron schedule to purge the QSentry search results that are in your local KV store and are older than 24 hours.

You can clean the feed manually in the following way:
- From the Splunk UI navigate to `Apps > Qintel QSentry Add-on for Splunk > Reports` and find `qintel_qsentry_clean_cache` and click `Open in Search` 


# CUSTOM COMMANDS #
The following command is included as a part of the add-on:

 - qsentry
    - Search format: `QUERY | qsentry ip_field=<ip_field>"` 
    - Purpose: Retrieves context information for all of the given IP addresses from Qintel QSentry.


# Dashboard and Auto-Enrichment #

This add-on does not include dashboards. 

You need to follow these steps to add enrichment tags to events, and then install the `Qintel Dashboards App for Splunk`

1. From the Splunk Web home screen, select the "Settings" dropdown from the top menu bar.
2. Select "Event Types" from the dropdown
3. Click the "New Event Type" button to add a new event type
4. Configure the following:
    - Destination App: TA_Qintel_QSentry
    - Name: descriptive name of the event type
    - Search String: search string specifying the events to be enriched (e.g. "sourcetype=auth" or "host=10.1.1.1")
    - Tag(s): 'qintel', 'network'
5. Click "Save"

**Note: it is important that the Qintel QSentry Add-on for Splunk be configured as the "Destination App". If this is not possible, ensure the sharing permissions on the event type are such that the Qintel QSentry Add-on for Splunk can access it ("Everyone/Read" from "All Apps" is sufficient)**


## Returns

Splunk events are enriched with the following fields that are returned from Qintel QSentry:
```
qintel_asn
qintel_asn_name
qintel_tags
qintel_last_seen
qintel_descriptions
qintel_risk
```

# UNINSTALL APP #
To uninstall app, user can follow below steps: 

 - SSH to the Splunk instance 
 - Go to folder apps($SPLUNK_HOME/etc/apps) 
 - Remove the TA_Qintel_QSentry* folder from apps directory 
 - Restart Splunk


# Support
 - Email: integrations-support@qintel.com


# COPYRIGHT #

 - Copyright (c) 2009-2024 Qintel, LLC
