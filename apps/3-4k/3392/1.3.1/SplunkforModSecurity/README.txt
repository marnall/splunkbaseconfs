# ModSecurity® App for Splunk®


* ModSecurity App for Splunk provides operational and analytical dashboards to enhance visibility on your ModSecurity Web Application Firewall. The goal of this document is to provide installation information for the App.


# Version 1.3.1


# Release Notes

1.3.1: January 2019
- Disabled data model acceleration by default to meet standards. No dashboard update.

1.3: June 2017
- Enhanced the Tracking dashboard (dynamic alert details, colors, search optimization)
- Added the Performance dashboard	
- Added the ModSecurity Events data model
- Enhanced the Overview and Historical dashboards

1.2: March 2017
- Adjusted the ModSecurity Alerts data model to match Add-on 1.2 corrections
- Enhanced the Tracking dashboard (dynamic inputs)
- Added a default ModSecurity search

1.0: November 2016
- Initial release


# Upgrade Instructions

This version of the App needs version 1.4.2 of ModSecurity Add-on for Splunk.


# Prerequisites:


	1 - Deploy ModSecurity Add-on for Splunk on your Splunk platform. For distributed environments, ModSecurity Add-on for Splunk needs to be deployed on the Search Head as well as on Indexer(s).


	2 - Deploy TA-user-agents as its User-Agent lookup is being used (https://splunkbase.splunk.com/app/1843/)


	3 - Collect audit data from a ModSecurity Web Application Firewall using Splunk Universal Forwarder as described in ModSecurity Add-on for Splunk documentation.


# Collect ModSecurity audit logs


	Your Splunk Universal Forwarder hosting ModSecurity should be configured to monitor ModSecurity audit logs and forward it to your Splunk Indexer or Heavy Forwarder.


	To achieve this, a local inputs.conf should be manually configured or deployed via a Deployment Server to monitor modsec_audit.log file which default location is /var/log/httpd/modsec_audit.log


	A sample configuration is provided in the Add-on README directory:


	[monitor:///var/log/httpd/modsec_audit.log]
	sourcetype = modsec:audit


	If needed, please refer to "Monitor files and directories using the Universal Forwarder" on Splunk Docs.


	ModSecurity data can be indexed in the default main index as well as in a dedicated one.


	If the data is indexed in a dedicated index, this index should be searchable by default by the relevant role. This can be configured under Settings: Access controls : Roles : <Role to edit> : ModSecurity dedicated index (if any) should be added in "Indexes" as well as in "Indexes searched by default".


# Install ModSecurity App for Splunk:


	ModSecurity App for Splunk should be installed on your Splunk instance. For distributed environments, it needs to be deployed on the Search Head.


	To install the App, follow the usual path: Apps : Manage Apps : Install app from file : Browse file : Upload and restart Splunk.
	
	
# Configure ModSecurity App for Splunk:


	This App uses two data models - 'ModSecurity Events' & 'ModSecurity Alerts' - to provide faster results.
	
	
	Hence, both data models should be accelerated to the range that suits your needs.
	
	
	This can be done from Settings > Data Models > Edit Acceleration > Accelerate / Summary Range.
	
	
	If a dedicated index is used, consider updating the root search (or constraint) of the data model with the configured index.
	
	
	For instance, the root search for the 'ModSecurity Alerts' data model is 'sourcetype="modsec:audit" type="alert"'. With a dedicated index, it should be updated to the more efficient 'index=<dedicated_index>" sourcetype="modsec:audit" type="alert"'.
	
	
	This can be achieved from Settings > Data Models > Edit Datasets > Constraints > Edit.


# Notes


	While the 'Overview' & 'Historical' dashboards provide statistics based on accelerated data, the Tracking dashboard aims at facilitating investiagtions.


	Its main search query uses the mvexpand function to expand the values of each alerts which resides in the multivalue field "message_extended" into separate events. 


	Instead of considering this event which can possibly gather several alerts:


	[...]
	--c7036611-H--
	Message: Warning. Match of "rx ^apache.*perl" against "REQUEST_HEADERS:User-Agent" required. [id "990011"] [msg "Request Indicates an automated program explored the site"] [severity "NOTICE"]
	Message: Warning. Pattern match "(?:\\b(?:(?:s(?:elect\\b(?:.{1,100}?\\b (?:(?:length|count|top)\\b.{1,100}?\\bfrom|from\\b.{1,100}?\\bwhere) |.*?\\b(?:d(?:ump\\b.*\\bfrom|ata_type)|(?:to_(?:numbe|cha)|inst)r))|p_ ( :(?:addextendedpro|sqlexe)c|(?:oacreat|prepar)e|execute(?:sql)?| makewebt ..." at ARGS:c. [id "950001"] [msg "SQL Injection Attack. Matched signature: union select"] [severity "CRITICAL"]
	Stopwatch: 1199881676978327 2514 (396 2224 -)
	Producer: ModSecurity v2.x.x (Apache 2.x)
	Server: Apache/2.x.x
	[...]


	It allows to search within separated alerts as separate events and avoid inaccurate search results:


	Message: Warning. Match of "rx ^apache.*perl" against "REQUEST_HEADERS:User-Agent" required. [id "990011"] [msg "Request Indicates an automated program explored the site"] [severity "NOTICE"]

	Message: Warning. Pattern match "(?:\\b(?:(?:s(?:elect\\b(?:.{1,100}?\\b (?:(?:length|count|top)\\b.{1,100}?\\bfrom|from\\b.{1,100}?\\bwhere) |.*?\\b(?:d(?:ump\\b.*\\bfrom|ata_type)|(?:to_(?:numbe|cha)|inst)r))|p_ ( :(?:addextendedpro|sqlexe)c|(?:oacreat|prepar)e|execute(?:sql)?| makewebt ..." at ARGS:c. [id "950001"] [msg "SQL Injection Attack. Matched signature: union select"] [severity "CRITICAL"]


	Log reference: ModSecurity 2 Data Formats (https://github.com/SpiderLabs/ModSecurity/wiki/ModSecurity-2-Data-Formats)


	There is a prior App for ModSecurity that was developed by Martin Brolin. Thanks to him as certain of its extractions and settings have been re-used.


# For any help on this App, contact splunk@nomios.fr




