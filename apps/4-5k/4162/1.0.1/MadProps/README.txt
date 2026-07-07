# Mad Props


When configuring Splunk to onboard data, it is a best practice to configure the six following props.conf parameters: TIME_PREFIX, TIME_FORMAT, MAX_TIMESTAMP_LOOKAHEAD, SHOULD_LINEMERGE, LINE_BREAKER and TRUNCATE.

By doing so, Splunk will know how to process events and will avoid spending resources guessing it. Hence, configuring these parameters - sometimes referred to as the magic six - is said to enhance indexing performances. 

Mad Props lets you quickly find out how are configured the magic six props.conf parameters on your Indexers by browsing configuration through API calls. Additionally, Mad Props provides a handy sourcetype browser that facilitate configuration checking between mutually dependent attributes from props.conf and transforms.conf.


# Version 1.0.1


# Release Notes


1.0.0: September 2018
- Initial release

1.0.1: September 2018
- Minor fixes


# Insight

This best practice of configuring the magic six props.conf parameters is mentioned in Andrew Duca's .conf2015 session "Data On-Boarding".

The App checks the configuration of your Indexers by calling the configs/conf-props API endpoint, and by differentiating between configured parameters and those left unchanged.

With this knowledge, a configuration score is calculated for each sourcetype. However, occasions arise where configuring certain parameters is not relevant. To avoid messing the score, a set of lookups lets you whitelist either apps, sourcetypes, or parameters.


# Prerequisites


Deploy Lookup File Editor (https://splunkbase.splunk.com/app/1724/) on your Splunk Search Head.


# Configuration Steps

1 - Install the App on your Splunk Search Head(s).

2 - Provide the App with the hostname(s) of your Indexer(s) by following the initial configuration of the App.

For a standalone Splunk platform, use "local" or "*"

For a single Indexer platform, use the hostname of the Indexer.

For a platform with multiple Indexers, use wildcards to match the hostnames of the Indexers.

To integrate your Heavy Forwarder(s), see Notes at the bottom of this README.

To adjust configuration later on, use the "App Configuration" view.

3 - Four lookups are being used within this app.

The madprops_active_sourcetypes_lookup maintains a list of active (last 24h) sourcetypes.

The madprops_sourcetypes_whitelist_lookup lets you whitelist entire sourcetypes from the results.

The madprops_parameters_whitelist_lookup lets you whitelist specific parameters within a particular sourcetype.

The madprops_apps_whitelist_lookup lets you whitelist Apps from the searches.

First, follow these three steps first:

- populate the madprops_active_sourcetypes_lookup first by going to "Whitelisting / Generate Base Lookups" and hitting "Run" for "Mad Props - 01 - Generate initial lookup for active sourcetypes".

- populate empty lookups for each whitelist lookup by going to "Whitelisting / Generate Base Lookups" and hitting "Run" for "Mad Props - 02 - Generate initial empty whitelist lookups".

- reload transforms.conf for the fresh lookups to be taken into account by using: http(s)://yourSplunkSearchHead/en-US/debug/refresh?entity=admin/transforms-lookup

Then, configure each of the other lookups by following the steps below:

- go to "Whitelisting / Generate Base Lookups" and generate a base lookup by hitting "Run" for each report from 03 to 05.

- go back to the App, and go to "Whitelisting / Export Base Lookups" and successively hit "Export" each base lookup.

- go to "Whitelisting / Import Base Lookups Data" and successively import and save each base lookup exported at the previous step to the matching whitelisting lookup.

- got to "Whitelisting / Edit Lookups" and edit the lookups as needed by selecting the lookup and by clicking on the rows you want the value to be inverted.

To ease configuration, the following Apps have been whitelisted by default in the madprops_apps_whitelist_lookup: learned, search, splunk_archiver, splunk_instrumentation, splunk_monitoring_console, system.

4 - The "Magic 6 Checker" view contains a hyperlink for the "Data Quality" dashboard from the Monitoring Console. This dashboard reports issues with event processing (See https://docs.splunk.com/Documentation/Splunk/latest/DMC/Dataquality).

The hyperlink is located in the panel at bottom of the page. While it should be working as-is with a standalone platform, it should be adjusted to target the Splunk instance where the Monitoring Console resides in a distributed environment.

5 - If deployed on an earlier version of Splunk (pre 7.1) add 'color="#333333"' to the first line of the default navigation menu (Settings > User interface > Navigation menus > default).


# Use the App


The "Magic 6 Checker" dashboard lets you select one or more sourcetypes to check whether the magic six parameters of props.conf have been configured. It provides additional information for each of these parameters as well as examples through Regex101.

While whitelisted sourcetypes as well as sourcetypes from whitelisted Apps are excluded from the sourcetype selector, whitelisted parameters are highlighted. The main panel lets you drilldown to the "Whitelisting / Edit Lookups Automatically" view.


The "Magic 6 Score" dashboard provides an overall scoring for the configuration of the magic 6 parameters on your Indexer(s) and Heady Forwarder(s). It also provides the list of the various sourcetypes along with their configuration score.

Whitelisted sourcetypes as well as sourcetypes from whitelisted Apps are excluded from the results. Whitelisted parameters on the other hand are taken into account in the score calculations. The main panel lets you drilldown back to the "Magic 6 Checker" dashboard.


The "Sourcetype Browser" dashboard should facilitate sourcetype browsing as it returns, for a given sourcetype, props.conf parameters as well as its linked transforms.conf stanzas, operation which usually requires many more steps. 

By default, only configured attributes of selected sourcetypes are highlighted. However, default attributes can also be displayed by switching the "Attribute values" link input.


The "Sourcetype/App Locator" dashboard lets you quickly find out in which App is configured a given sourcetype, or what sourcetypes are configured in a particular App.


The Whitelisting section usage is detailed in the configuration steps above. Note that the "Edit Lookups" view lets you whitelist items or cancel whitelisting by clicking on the selected item. Reloading the panel will let you check on the lookup update.

After the initial configuration, you will inevitably configure new sourcetypes and deploy new Apps, the "Control Lookups" view helps you finding out any unlisted or unintentionally whitelisted sourcetype.


# Notes


As Heavy Forwarder(s) are also responsible for processing data streams, magic six props.conf parameters should be configured on these instances as well. Hence, make sure your Heavy Forwarder(s) have been configured as search peers from your Search Head(s), and adjust the hostname regex in the "App Configuration" view to match them.

Splunkbase Apps like "Data Curator" and "props helper" share the same purpose as it also helps on data on boarding.

The great and handy "Config Quest" App (https://splunkbase.splunk.com/app/3696/) has been an inspiration for building this App. 


# For any help or suggestion on this App, contact d2si-spk [at] protonmail.com


