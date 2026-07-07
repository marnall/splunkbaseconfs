# Internal Billing


Internal Billing App provides means to monitor how the various client teams using your Splunk platform consume their license allowed quota.

To do so, Internal Billing App lets you map your Splunk indexes to their client team owner and assign each client team a daily license quota.

The provided insights aim at helping you follow your client team’s license consumption on your platform.


# Version 1.0.4


# Release Notes


1.0.0: May 2018
- Initial release
		
1.0.1: June 2018	
- Added contact info to quotas by team lookup
		
1.0.2: June 2018	
- Documentation updates for App certification
	
1.0.3: September 2018
- Fixed an earliest/latest token from a panel
- Updated the installation process to ease App upgrades

1.0.4: September 2018
- Fixed App logo & README

# Insight


Internal Billing App shares the same purpose as the Chargeback Analysis for Splunk App (https://splunkbase.splunk.com/app/2967/).

We just had to build our simple version for a specific use case and wanted to share it on Splunkbase.

The App has two external dependencies.

It uses Luke Murphey's great Lookup File Editor (https://splunkbase.splunk.com/app/1724/) to ease lookup building.

It also uses Discovered Intelligence's Meta Woot! (https://splunkbase.splunk.com/app/2949/).

This later App provides great insights from your Splunk metadata and license usage.

To build its knowledge on your license consumption, it uses a dedicated accelerated Data Model.

The Meta Woot License Usage Data Model aggregates data from your license_usage.log file ingested in the _internal index.

We thought it was more convenient to use this Data Model because we do use Meta Woot and wanted to avoid having to maintain a duplicate data model and because we are planning to release another App also based on this Data Model.


# Prerequisites


1 - Deploy Lookup File Editor (https://splunkbase.splunk.com/app/1724/) on your Splunk Search Head.

2 - Deploy Meta Woot! (https://splunkbase.splunk.com/app/2949/) on your Splunk Search Head.

3 - Configure acceleration for Meta Woot's License Usage Data Model.

It can be achieved by ticking Accelerate from Settings > Data models > Meta Woot License Usage > Edit > Edit Acceleration and by setting the Summary Range to 7 days.

4 - Configure global permissions for Meta Woot's License Usage Data Model to be able to access the aggregated data outside of Meta Woot!.

This can be done by selecting 'Display For All apps' from Settings > Data models > Meta Woot License Usage > Edit > Edit Permissions and by making sure to at least set read permissions for the role that will be used to launch the App.

5 - Configure the '_internal' index as an allowed index for your role. As Meta Woot's License Usage Data Model gathers data from the '_internal' index, your role should be able to query this index.

It can be set by adding '_internal' index to the allowed indexes attached to Settings > Access controls > Roles > [Your role].

6 - In a distributed environment, make sure internal data from your License Master is being indexed on your Indexers and therefore available from your Search Head(s).

You should retrieve results from the following query: index="_internal" sourcetype="splunkd" source="*license_usage.log" type="Usage"

7 - If deployed on an earlier version of Splunk (pre 7.1) add 'color="#333333"' to the first line of the default navigation menu (Settings > User interface > Navigation menus > default).


# Configuration Steps


# App deployment


Deploy the App on your Search Head.


# Populate indexes_mapped_to_teams_lookup


This lookup maintains a mapping between indexes and their owners, the client teams.

This lookup consists in a simple index -> team association.

To help you build this lookup you can use dedicated savedsearches available from Internal Billing UI > Configure > Lookup bases and alerts.

From there, pick "Generate initial empty lookups" and choose "Open in Search".

This will build generate empty csv files for all needed lookups.

Then, pick "Generate lookup base to map teams to indexes" and choose "Open in Search".

This will build a list of your indexes (those filled yesterday) and associate them with a temporary "TBD" team, and save a lookup file named 'indexes_mapped_to_teams_lookup_base.csv'.

This base lookup can be accessed App's UI > Configure > Map indexes to teams (base lookup) where it can be manually populated with proper teams.

Once done, export the result from Lookup Editor UI.

Then, the exported base lookup can be imported into the actual lookup from App's UI > Configure > Map indexes to teams.

Finally, you should be able to browse the lookup you have just updated by browsing it through a dedicated view reachable from the App's UI > Browse > Mapped indexes.

If your organization has a CMDB you can pull data from, you can alternatively automate this whole process and thus maintain an automatically updated version of the lookup.


# Populate quotas_assigned_to_teams_lookup


This lookup maintains a mapping between teams and their allowed license quota.

This lookup consists in a simple team -> quota association.

It also lets you associate a team with its contact.

To help you build this lookup you can use a dedicated savedsearch available from Internal Billing UI > Configure > Lookup bases and alerts.

From there, pick "Generate lookup base to attribute quotas to teams" and choose "Open in Search".

This will build a list of your teams from the previously configured lookup and associate them with a temporary "TBD" quota, and save a lookup file named 'quotas_assigned_to_teams_base.csv'.

This base lookup can be accessed App's UI > Configure > Assign quotas to teams (base lookup) where it can be manually filled with agreed quotas.

Once done, export the result from Lookup Editor UI.

Then, the exported base lookup can be imported into the actual lookup from App's UI > Configure > Assign quotas to teams.

Finally, you should be able to browse the lookup you have just updated by browsing it through a dedicated view reachable from the App's UI > Browse > Assigned quotas.


# Validate your lookups using Inspect view.


From the App's UI > Inspect, you can use the configured panels to validate your lookups.

The provided queries will look for indexes mapped to multiple teams, unlisted indexes or teams, and undefined quotas.

These queries are also available as alerts which can be enabled from App's UI > Configure > Lookup bases and alerts


# Use the App


Once ready to use, Monitor and Investigate are the two main dashboards to visit.

Monitor provides data on license consumption by team on the last 3 days.

Drilldown capabilities let you sharpen a particular team's consumption to the index, sourcetype and host levels.

Whenever you need an historical trend, the Investigate dashboard can help.

The Investigate dashboard also provide drilldown capabilities that will let you expand an initial result.


# Alerts


Several alerts are included in this App.

Whenever a team exceeds its daily-allowed license quota, the 'Exceeded quota' alert is triggered.

Other alerts have been converted from the Inspect dashboard queries.

All alerts have been disabled by default. Adjust and enable them as preferred.


# Additional notes


Note that most of the queries configured in this App are querying the summarized data (summariesonly=true).

Hence, if you need to be able to query data older than the configured Summary Range for the Data Model (i.e. 7 days), you need either to extend the Summary Range or adapt the searches to not only look for summarized data.

The latter option can be achieved with summariesonly=false clause instead of summariesonly=true in queries.

Note that we designed this App to map teams to indexes. Depending on your context, you might rather need to map your client teams with sourcetypes or even with hosts.


# For any help or suggestion on this App, contact d2si-spk [at] protonmail.com


