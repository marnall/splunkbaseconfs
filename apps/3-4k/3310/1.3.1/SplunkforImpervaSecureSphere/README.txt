# Imperva SecureSphere® App for Splunk®


* Imperva SecureSphere App for Splunk provides operational and analytical dashboards to enhance visibility on your Imperva SecureSphere appliance.


# Version 1.3.1


# Release Notes


1.3.1: January 2019
- Only updated version reference (1.x.x instead of 1.x) to meet standards. No dashboard update.

1.3: April 2017
- Fixed a drilldown to raw event issue (thanks to James)

1.2: January 2017
- Updated JavaScript code used to ease multiselect with a 6.5 compliant version (thanks to hobbes3 - GitHub)

1.1: November 2016
- 6.5 ready

1.0: September 2016	
- Initial release


# Prerequisites:


	As Imperva SecureSphere App for Splunk is based on field extractions and eventtypes brought by Splunk Add-on for Imperva SecureSphere WAF, the latter Add-on must be deployed on your Splunk platform.
	
	
	This Add-on can be downloaded from Splunkbase (https://splunkbase.splunk.com/app/2874/). Its deployment is documented on Splunk Docs (http://docs.splunk.com/Documentation/AddOns/latest/ImpervaWAF/About).


# Index Imperva SecureSphere syslog data:

	
	This part is documented on Splunk Docs as it goes along with the deployment of Splunk Add-on for Imperva SecureSphere WAF (http://docs.splunk.com/Documentation/AddOns/released/ImpervaWAF/Setup).

	
# Install Imperva SecureSphere App for Splunk:


	Imperva SecureSphere App for Splunk should be installed on your Splunk instance. For distributed environments, it needs to be deployed on the Search Head instance.
	
	
	To install the App, follow the usual path: Apps : Manage Apps : Install app from file : Browse file : Upload and restart Splunk.
	
	
# Adjust color ranges on the single value panels:


	The Overview dashboards (Alerts, Intrusion Detection, Malware) display the number of alerts that have been indexed during the selected period of time. It also indicates how many of them have been allowed or blocked by the Imperva Appliance.
	
	
	Results can then be trimmed by web application and / or taken action.
	
	
	Color ranges have been defined on each single panel to enhance visibility on the results. But as the appropriate color fully depends on the number of alert events generated in your environment, it needs to be adjusted.
	
	
	To achieve this, calculating the average number of alert events for a given period could be helpful. This can be done by using the avg command.
	
	
	As for example, the following Splunk search will provide the daily average number of alert events:

	
	eventtype="imperva_waf" | bucket _time span=1d | stats count by _time | stats avg(count) as AverageCountPerDay
	
	
	It could of course be used with other Imperva eventtypes ("imperva_waf_security_ids" or "imperva_waf_worm").
	
	
	It could also be used to calculate the daily average number of blocked or allowed alert events by adding the action argument to the search:
	
	
	eventtype="imperva_waf_worm" action="blocked" | bucket _time span=1d | stats count by _time | stats avg(count) as AverageCountPerDay


# For any help on this App, contact splunk@nomios.fr


