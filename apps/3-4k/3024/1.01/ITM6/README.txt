################################################################################
# Introduction
################################################################################

The ITM6 App for Splunk can be used to index or view information from multiple 
ITM6 systems into Splunk using ITM6's SOAP and REST interfaces.

The app provides modular inputs that can be used to index ITM6 data, and 
commands which enable the display of data from ITM without indexing.


################################################################################
# Requirements
################################################################################

Splunk Enterprise version 6.3 is recommended for full functionality.

On Splunk versions < 6.3 only administrators can access the TEMS configuration
enndpoint in Splunk.  This stops non-admins from using the itmsoap and itmdash 
search commands.

The agent health modular input uses a KV store to store the most recent health
results.  Therefore version 6.2 is required if you intend to use this feature.

Splunk must be able to communicate on port 1920 and 15200 with any ITM6 
environment you add to the app.


################################################################################
# Installation instructions
################################################################################

	1. Download the application installation file (ITM6.spl)
	2. Use the install app from file option in Splunkweb


################################################################################
# Configuration/Usage instructions
################################################################################

Add the TEMS server details of the environment you wish to manage:

	1. From your Splunk Enterprise homepage navigate:
		ITM6 > Settings > Manage TEMS Connections > New
	
	2. Fill in the details for your TEMS


Collect data from ITM6:

	1. Navigate to data Inputs:
		Settings (Top right menu) > Data inputs
		
	2. Choose 'ITM6 Dash Input', 'ITM6 Object Input' or 'ITM6 SQL Input'
		Which should I choose?
			- Dash
				- Can get data from TDW
				- Drop down lists when choosing input
				- Uses more resource on the TEPS than SOAP
			- SOAP (Object)
				- returns human readable field names
				- can pull local historical data
			- SOAP (SQL)
				- more flexibility over what you query
				- offers the ability to time out the query and the TEMS
				- can pull local historical data
	

Display ITM data without indexing it:

	The itmsoap and itmdash search commands provide an interface to the TEMS SOAP 
	and the TEPS dashboard data provider interface.  The dashboard data browser 
	dashboard can help with generating search commands for itmdash, however
	knowledge of the ITM interfaces is required to use these commands.

	itmsoap tems=<tems> [sql=<sql> | fields=<field,...> table=<table> at=<All|All Hubs|All Remotes|tems name> nodelist=<agent|msl> [clause=<where clause>] [timeout=<secs>] [timefield=<timefield>] | object=<object> target=<target> [attribute=<attribute,...>] [afilter=<condition,...>] [timefield=<timefield>]
	
	itmdash tems=<tems> [endpoint=<endpoint>] [datasource=<datasource> [dataset=<dataset> [sourcetoken=<agent|msl> [properties=<properties>] [condition=<condition>] [field_format=<label|id>] [earliest=now latest=now]]]]
	
	
Healthcheck your environment:

	The ITM6 Daily Agent Healthheck script is provided to help determine if your
	agents are in a healthy state.  This script is a work in progress, and has only
	been tested on a small environment.
	
	Currently the script attempts to collect the operations log from all agents to
	determine if the agent is responsive.

	1. Navigate to data Inputs:
		Settings (Top right menu) > Data inputs
		
	2. Choose 'ITM6 Daily Agent Health Check'	
		
		A cron style Interval is recommended so you can choose the time that the
		healthcheck runs