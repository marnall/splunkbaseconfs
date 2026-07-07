Welcome to InfoSec App for Splunk

************************
*** BEFORE YOU BEGIN ***
************************

PREREQUISITES - IMPORTANT: WITHOUT THESE, THE APP WILL NOT BE OF MUCH USE


- The following free Splunk Add-ons must be installed before you can start using InfoSec App:
	- Splunk Common Information Model (CIM): https://splunkbase.splunk.com/app/1621/
	- Punchcard visualization: https://splunkbase.splunk.com/app/3129/
	- Force Directed visualization: https://splunkbase.splunk.com/app/3767/ (use add-on version 3.0.1 in Splunk Cloud)
    	- Lookup File Editor: https://splunkbase.splunk.com/app/1724/ (new requirement starting from InfoSec v1.5)
    	- Sankey Diagram visualization: https://splunkbase.splunk.com/app/3112/ (new optional prerequisite for the experimental VPN Access dashboard starting from v1.5.3)

- The following Data Models must be accelerated: 
	- Alerts
	- Authentication
	- Change
	- Intrusion_Detection
	- Network_Sessions
	- Network_Traffic
	- Endpoint
	- Web

- All data used by InfoSec app must be Common Information Model (CIM)-compliant. The easiest way to accomplish that is to use CIM-compliant Splunk Add-ons for your security data sources


WHERE TO INSTALL THE APP

The app can be installed on a standalone Splunk server, a Search Head or a Search Head Cluster. In a distributed environment do not install the app on Indexers; the app should only be installed on Search Head(s).


*****************************
*** THE REST OF THE STORY ***
*****************************

WHAT INFOSEC CLOUD APP DOES

InfoSec Cloud app for Splunk is your starter cloud security pack for Splunk. InfoSec Cloud app is designed to address the most common security use cases, including continuous monitoring and security investigations. InfoSec Cloud app also includes a number of advanced threat detection use cases. All of the components of InfoSec Cloud app can be easily expanded using free security resources available for Splunk like Security Essentials app for Splunk: https://splunkbase.splunk.com/app/3435


ADDITIONAL TECHNICAL DETAILS SO YOU KNOW HOW THE APP WORK

InfoSec Cloud app is designed to use only basic Splunk functionality so it is easier for you to make the app your own by modifying and adding content from other free Splunk resources like Splunk Security Essentials (https://splunkbase.splunk.com/app/3435/)

InfoSec Cloud app uses the following macros you can modify to better match your Splunk configuration:
- Splunk indexes with security data `infosec-cloud-indexes`. Default value: index="*"

InfoSec app uses KV Store lookups for user and host information. Lookups are infosec_users and infosec_hosts. You will need to populate the lookups with your user and host information. Investigation dashboards will show user and host information if it is available in the lookups. 


*********************
*** RELEASE NOTES ***
*********************


Version 1.0.0 - 
Initial release


Version 1.1.0 - 
Addition of cloud_billing dashboard. In order to populate this dashboard, the treemap visualization must be installed and the Department_Lookup.csv lookup must be filled in. The Department_Lookup.csv can be found in InfoSec_Cloud_App_for_Splunk/lookups. You will need to populate this lookup with your various departments and its correlating account_id information. This information is utilized in the "Costs By Department" panel.

Version 1.1.3 - 
Splunk 10.x compatible.