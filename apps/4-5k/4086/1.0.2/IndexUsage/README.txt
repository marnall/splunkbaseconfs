# Index Usage


When an index reaches its maximum size, Splunk deletes the oldest indexed events. This can occur whenever an index has not been correctly sized.

Splunk Monitoring Console already provides means to monitor how your indexes are filling up helping you spotting any full or nearly full index.

Therefore, you usually just have to extend the size of a nearly full index to avoid losing data.

However, this task could become redundant if indexes' size are being extended with no regards for the actual volume of data they ingest.

This can be avoided by having your indexes correctly sized.

To correctly size an index, you have to be able to predict what will be its size when it reaches the configured retention period.

To be able to estimate that final size, you obviously need to know how much data this index will ingest every day.

The problem is that it could be difficult to know the average daily volume of data that will receive an index beforehand. This volume can also vary widely over time.

This App provides visibility on your indexes' filling by calculating the final size of each index based on the daily average volume of data ingested, and by comparing it to the current index configuration.

Hence, the goal of this App is to provide a simple way to check on the sizing of your indexes in order to avoid data loss and redundant index re-sizing.


# Version 1.0.2


# Release Notes


1.0.0: July 2018

- Initial release
		
1.0.1: September 2018

- Fixed 'Index Configuration' view

1.0.2: September 2018

- Minor fix


# Insight


To check on the daily volume of data ingested by each index, this App uses Discovered Intelligence's Meta Woot! (https://splunkbase.splunk.com/app/2949/)

This later App provides great insights from your Splunk metadata and license usage.

To build its knowledge on your license consumption, it uses a dedicated accelerated Data Model.

The Meta Woot License Usage Data Model aggregates data from your license_usage.log file ingested in the _internal index.

We thought it was more convenient to use this Data Model because we do use Meta Woot and wanted to avoid having to maintain a duplicate data model and also because we are already using this Data Model with our previous App, Internal Billing (https://splunkbase.splunk.com/app/4041/).


# Prerequisites


1 - Deploy Meta Woot! (https://splunkbase.splunk.com/app/2949/) on your Splunk Search Head.

2 - Configure acceleration for Meta Woot's License Usage Data Model.

It can be achieved by ticking Accelerate from Settings > Data models > Meta Woot License Usage > Edit > Edit Acceleration and by setting the Summary Range to 7 days.

3 - Configure global permissions for Meta Woot's License Usage Data Model to be able to access the aggregated data outside of Meta Woot!.

This can be done by selecting 'Display For All apps' from Settings > Data models > Meta Woot License Usage > Edit > Edit Permissions and by making sure to at least set read permissions for the role that will be used to launch the App.

4 - Configure the '_internal' index as an allowed index for your role. As Meta Woot's License Usage Data Model gathers data from the '_internal' index, your role should be able to query this index.

It can be set by adding '_internal' index to the allowed indexes attached to Settings > Access controls > Roles > [Your role].

5 - In a distributed environment, make sure internal data from your License Master is being indexed on your Indexers and therefore available from your Search Head(s).

You should retrieve results from the following query: index="_internal" sourcetype="splunkd" source="*license_usage.log" type="Usage"

6 - If deployed on an earlier version of Splunk (pre 7.1) add 'color="#333333"' to the first line of the default navigation menu (Settings > User interface > Navigation menus > default).


# Configuration Steps


REST URIs for rest API calls:

Splunk queries part of this App consist in REST API calls. It should work as-is if your Splunk platform is quite simple since the queries are expecting results from your Indexer(s) only.

If, however, your Splunk platform is more complex (i.e. if the search peers configured on your Search Head(s) are not only Indexer(s)), then you might have to adjust queries by specifying the appropriate REST URI.

For instance, '| rest /services/data/indexes' would become '| rest splunk_server=<rest-uri> /services/data/indexes' with <rest-uri> possibly containing wildcards (i.e. '| rest splunk_server=splunk-indexer* /services/data/indexes').

Replication factor for Indexer Cluster:

To predict what will be the final size of an index, the following formula is being used in both 'Index usage' and 'Global usage' dashboards:

daily average volume indexed by indexer in GB x 0.5 (average compression) x replication factor (if applicable) x retention period in days

As the replication factor could only be obtained by making an API CALL to the Cluster Master, it has not been integrated in the queries.

Therefore, if you run an Indexer Cluster, you must find out what is the replication factor and then add it to the queries.

To find out what replication factor is applied to your Indexer Cluster, you can use the following query from you Cluster Master:

| rest splunk_server=local /servicesNS/-/-/configs/conf-server
| search replication_factor=*
| fields replication_factor site_replication_factor multisite eai:acl.app
| rex field=site_replication_factor "total\:(?<repFactor>\d+)"
| eval replication_factor=if(multisite==1,repFactor,replication_factor)
| fields - multisite site_replication_factor repFactor

Then, you should integrate its value to both queries.

In 'Index usage' dashboard, expectedIndexSizeGB=consumedDailyPerIndexerGB*0.5*frozenTimePeriodDays would become expectedIndexSizeGB=consumedDailyPerIndexerGB*0.5*<your_replication_factor>*frozenTimePeriodDays.

In 'Global usage' dashboard, expectedIndexSizeGB=round((consumedDailyGB*0.5*frozenTimePeriodDays),0) would become expectedIndexSizeGB=round((consumedDailyGB*0.5*<your_replication_factor>*frozenTimePeriodDays),0).

In any case, double check on the value obtained for expectedIndexSizeGB to make sure it is coherent to your platform.


# App deployment


Deploy the App on your Search Head.


# Use the App


Once ready to use, 'Index usage' is the main dashboard to visit as it provides a glimpse into your indexes statistics and configurations.

From there you can drilldown to either 'Index Configuration' or 'Time-base ingestion' dashboard.

The 'Time-based ingestion' dahsboard provides the daily ingestion volume by index for a wider period - 30 days - displayed as a timechart. You can also pick several indexes from there.

Comparing to the 'Index usage' dashboard, the 'Global usage' dashboard provides global insights on your indexes' sizing and configuration.

The 'Age of data' dahsboard lets you quickly check on the age of the data for each index.

Finally, the 'Index configuration' dashboard let you browse your current index configuration to check on the various parameters. You can pick multiple indexes and configuration parameters for comparison.


# Alert


One alert is included in this App.

Whenever an index reaches 90% of its maximum size, the 'Index nearly full' alert is triggered.

The alert has been disabled by default. Adjust and enable it as preferred.


# For any help or suggestion on this App, contact d2si-spk [at] protonmail.com


