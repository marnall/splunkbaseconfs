### About

This application contains dashboards for analysing and searching in Nessus/Tenable vulnerability scan logs.

### Installation

The application is meant to be installed on the Splunk search heads where you want to use the security dashboards, preferably on the same search head as Splunk ES, for easy utilization of asset lists.

The easiest way to get data from Tenable to Splunk in the correct format is to use the TA "Tenable Add-On for Splunk" (https://splunkbase.splunk.com/app/4060). The logs collected by this TA will work with the dashboards in this application, given that the configuration steps are followed.

### Configuration

- Change the permission of the application to your needs.
- Add the appropriate indexes to the macro `nessus_indexes`.
- Add any vulnerabilities you don't want to show in the dashboards to the lookup `whitelisted_vulnerabilities.csv`, with the severity sat to "ignored". Note that you can also use wildcard to exclude for example all vulnerabilities on certain hosts.
- Change the macro `nessus_set_host_environment` to properly sort your hosts by environment based on naming conventions, for extra analysis related environments. This step is not needed if the Splunk ES lookup `asset_lookup_by_str` is properly configured with the `production_level` field and available.

Note that not all these steps are required for the application to work. If not all steps are done properly some panels in some dashboards might not work as intended, but if so you can always just remove those panels.

### Optional configuration

- If you have this application installed on the same search head as Splunk ES, make sure the lookup `asset_lookup_by_str` is shared with this application, and add the lookup to the macro `nessus_bunit_lookup`, for extra analysis related to business groups.
- If you have an overview of what networks belongs to your organization, add them to the lookup `internal_networks`. If you already have the networks stored in another lookup, you could also change the dashboards to use your lookup instead. Skipping this step will not have a major impact, but will remove some analysis related to which networks are scanned and not.
- Change the scheduled report "Nessus Host Summary Index Search" to wite summary logs to the appropriate index. This summary index should also by added to the macro `nessus_indexes`. This step is only needed if you have custom input scripts directly to Nessus, not using the Tenable Add-On for Splunk.

Note that some of the additional enrichment information on the dashboard requires extra information from Nessus APIs. As of now  I have not been able to submit my input scripts for these Nessus APIs to Splunkbase. Dashboards will still work, but some information in some panels will be missing.
