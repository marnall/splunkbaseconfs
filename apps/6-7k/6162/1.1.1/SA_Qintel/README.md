# Qintel Dashboards App for Splunk #

# OVERVIEW #
The Qintel suite of technology add-ons allows you to enrich your various log data from Qintel’s Patch Management Intelligence (PMI), and QSentry services. The Qintel Dashboards App provides you with visualizations of this Qintel enriched data to allow you to take quick action.

 - Author: Qintel
 - Version: 1.1.1
 - Creates Index: False
 - Has index-time operation: True
 - Implements summarization: False
 - Prerequisites: Qintel PMI or QSentry add-on's

# COMPATIBILITY MATRIX #
 - Splunk Enterprise version: 8.x, 9.0, 9.1, 9.2
 - OS: Platform independent
 - Vendor Products: Qintel PMI, Qintel QSentry Feed, Qintel QSentry

# RELEASE NOTES (Version 1.1.1) #
- default.meta changes to restrict write access for application knowledge objects

# RELEASE NOTES (Version 1.1.0) #
- update dashboard visualizations 

# RELEASE NOTES (Version 1.0.1) #
- Integrates new Qintel visualizations
- integrates macros to allow greater customization 

# INSTALLATION #
Follow the below-listed steps to install an app from the bundle:

 - Download the App package.
 - From the UI navigate to Apps > Manage Apps.
 - In the top right corner select Install app from file.
 - Select Choose File and select the App package.
 - Select Upload and follow the prompts.
 - Restart the Splunk to complete the installation.

# CONFIGURATION #
The app itself does not need to be configured. 
It expects either Qintel PMI Add-on for Splunk, Qintel QSentry Add-on for Splunk, or Qintel QSentry Feed Add-on for Splunk to be installed and the steps to be followed for 'auto-enrichment'. 
When these are configured properly, the dashboard in this app will populate automatically.

## MACROS #
There are three macro's that can be customized for your environment. 

Qintel Index is the destination index that the Qintel Apps will store the stash values in, by default this is 'main'.
Qintel Source Indexes are the indexes that are searched when looking for data to autoenrich, be default this is all indexes.
Qintel IP Search is the custom search command that is integrated into the 'Threat Intel - Overview' dashboard for more easily pivoting.

- `qintel_index`
  - default value: definition = index="main"
- `qintel_source_indexes`
  - default value: definition = ()
- `qintel_ip_search`
  - default value: definition = qsentry


# UNINSTALL APP #
To uninstall app, user can follow below steps: 

 - SSH to the Splunk instance 
 - Go to folder apps($SPLUNK_HOME/etc/apps) 
 - Remove the TA_Qintel_PMI* folder from apps directory 
 - Restart Splunk


# Support
 - Email: integrations-support@qintel.com


# COPYRIGHT #

 - Copyright (c) 2009-2021 Qintel, LLC
 