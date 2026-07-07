# Axway® API Gateway App


Axway API Gateway App provides means to facilitate the troubleshooting of Axway API Gateway issues.

The App also brings visibility on the performance of the provided service.


# Version 1.0.0


# Release Notes


1.0.0: October 2019

- Initial release

# Prerequisites


Install Axway API Gateway Add-on.

Index Axway API Gateway open logging data using the Add-on.


# App deployment


Install the App on your Splunk platform.

For distributed environments, the App only needs to be installed on the Search Head.


# Configuration


Edit event type 'axway_api_gw_logs' to match your configuration.

Got to 'Settings > Event types' and click on 'axway_api_gw_logs'.

The default configuration is: sourcetype="axway:apigateway:traffic:json".

So make sure the index containing your open logging data is configured as a 'default' index. If not adapt the event type to match your context (i.e. index="<index>" sourcetype="axway:apigateway:traffic:json").


# Insights

The App includes 3 dashboards, 'Console', 'Investigation' and 'Performance'


'Console' dashboard:

- Search for specific transactions using various filters;

- Choose which filters to display via 'Filter Selection';

- Search for specific or wildcard paths;

- Drilldown from a particular transaction to the 'Investigation' dashboard.


'Investigation' dashboard:

- Search Filter Execution Path and detailed transaction information;

- User a correlation ID (if not coming from the Console dashboard);

- 'Filter Execution Path' can be displayed as table or raw JSON;

- JSON auto expands;

- Displays up to 40 request/response panels.


'Performance' dashboard:

- Obtain performance statistics for a given service and/or method;

- Search by service or by service and method.


# Additional notes


This App does not yet provide visibility on transaction payloads.


# For any help or suggestion on this App, contact d2si-spk [at] protonmail.com


