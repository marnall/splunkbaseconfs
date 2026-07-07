# Qintel PMI Add-on for Splunk #

# OVERVIEW #
Qintel’s Patch Management Intelligence (PMI) product reports vital context around actively exploited Common Vulnerabilities and Exposures (CVEs). PMI is a repository of exploited vulnerabilities that are known by Qintel to be leveraged by adversaries of all stripes.

The Qintel PMI Add-on for Splunk allows you to perform real time queries of PMI from vulnerability scan and CVE-related data logs automatically or by search one at a time.

 - Author: Qintel
 - Version: 1.1.0
 - Creates Index: False
 - Has index-time operation: True
 - Implements summarization: False
 - Prerequisites: Qintel Crosslink Token, Splunk Common Information Model (CIM) App

# COMPATIBILITY MATRIX #
 - Splunk Enterprise version: 8.x, 9.0, 9.1, 9.2
 - OS: Platform independent
 - Vendor Products: Qintel PMI

# RELEASE NOTES (Version 1.1.0) #
- Fixed JQuery 3.5 compatability
- Upgraded underlying splunk libraries (splunklib, splunktalib, solnlib, splunktaucclib)
- Updated documentation

# RELEASE NOTES (Version 1.0.0) #
- Integrates new Qintel helper file to query PMI and temporarily cache search results
- creates `pmi` custom search command

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

 - From the Splunk UI navigate to `Apps > Qintel PMI Add-on for Splunk > Configuration`.
 - Click on Qintel PMI Configuration and enter your Crosslink Client ID and Crosslink Client Secret.
 - Optionally, enter a PMI API URL if you want to use a non-default URL.
 - Click on Save button.
 - The app is now configured and is able to query Qintel PMI.

Logging

 - User can configure the log level by navigating to `Apps > Qintel PMI Add-on for Splunk > Configuration` and selecting Logging.
 
# Caching #
This TA temporarily stores PMI search data results into a local key value store.

You can view the contents in the following way:
 - From the Splunk UI navigate to `Apps > Qintel PMI Add-on for Splunk > Datasets`.
 - Click on `qintel_pmi_cache`.

## Cleaning the Cache ##
This TA installs a saved search that runs every 5 minutes on a cron schedule to purge the PMI search results that are in your local KV store and are older than 24 hours.

You can clean the feed manually in the following way:
- From the Splunk UI navigate to `Apps > Qintel PMI Add-on for Splunk > Reports` and find `qintel_pmi_clean_cache` and click `Open in Search` 


# CUSTOM COMMANDS #
The following command is included as a part of the add-on:

 - pmi
    - Search format: `QUERY | pmi cve_field=cve` 
    - Purpose: Retrieves context information for all of the given CVEs from Qintel PMI.


# Dashboard and Auto-Enrichment #

This TA does not include dashboards. 

After installing the Splunk CIM, when you configure your vulnerability scanner to upload logs the events should automatically be tagged appropriately.

If the events aren't being tagged appropriately you need to follow these steps to add enrichment tags to events, and then install the `Qintel Dashboards App for Splunk`

1. From the Splunk Web home screen, select the "Settings" dropdown from the top menu bar.
2. Select "Event Types" from the dropdown
3. Click the "New Event Type" button to add a new event type
4. Configure the following:
    - Destination App: TA_Qintel_PMI
    - Name: descriptive name of the event type
    - Search String: search string specifying the events to be enriched (e.g. "sourcetype=auth" or "host=10.1.1.1")
    - Tag(s): 'vulnerability', 'report'
5. Click "Save"

**Note: it is important that the Qintel PMI Add-on for Splunk be configured as the "Destination App". If this is not possible, ensure the sharing permissions on the event type are such that the Qintel PMI Add-on for Splunk can access it ("Everyone/Read" from "All Apps" is sufficient)**


## Returns

Splunk events are enriched with the following fields that are returned from Qintel PMI:
```
qintel_cve_actors
qintel_cve_actor_types
qintel_cve_affected_system
qintel_cve_affected_version
qintel_cve_patches
qintel_cve_exploit_types
qintel_cve_first_observed
qintel_cve_last_observed
qintel_cve_recently_observed
```

# UNINSTALL APP #
To uninstall app, user can follow below steps: 

 - SSH to the Splunk instance 
 - Go to folder apps($SPLUNK_HOME/etc/apps) 
 - Remove the TA_Qintel_PMI* folder from apps directory 
 - Restart Splunk


# Support
 - Email: integrations-support@qintel.com


# COPYRIGHT #

 - Copyright (c) 2009-2024 Qintel, LLC
