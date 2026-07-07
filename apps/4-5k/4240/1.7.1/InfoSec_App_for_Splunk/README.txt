Welcome to InfoSec App for Splunk

************************
*** BEFORE YOU BEGIN ***
************************

PREREQUISITES - IMPORTANT: WITHOUT THESE, THE APP WILL NOT BE OF MUCH USE

- At a minimum, you should have data from the following security sources collected by your Splunk environment:
	- Firewall data like Cisco ASA, Palo Alto Networks, Check Point, Juniper, Fortinet, etc.
	- Active Directory security logs (make sure that your audit policy enables logging failed and successful authentication attempts)
	- Antivirus/Malware data like McAfee, Symantec, Trend Micro, etc. 

- The following free Splunk Add-ons must be installed before you can start using InfoSec App:
	- Splunk Common Information Model (CIM): https://splunkbase.splunk.com/app/1621/
	- Punchcard visualization: https://splunkbase.splunk.com/app/3129/
	- Force Directed visualization: https://splunkbase.splunk.com/app/3767/ (use add-on version 3.0.1 in Splunk Cloud)
    	- Lookup File Editor: https://splunkbase.splunk.com/app/1724/ (new requirement starting from InfoSec v1.5)
    	- Sankey Diagram visualization: https://splunkbase.splunk.com/app/3112/ (new optional prerequisite for the experimental VPN Access dashboard starting from v1.5.3)

- The following Data Models must be accelerated: 
	- Authentication
	- Change (for app version 1.6.x and newer) or Change Analysis (for app version 1.5.3 and older)
	- Intrusion_Detection
	- Malware
	- Network_Sessions
	- Network_Traffic
	- Endpoint
	- Web (new requirement starting from InfoSec v1.5)

- All data used by InfoSec app must be Common Information Model (CIM)-compliant. The easiest way to accomplish that is to use CIM-compliant Splunk Add-ons for your security data sources


WHERE TO INSTALL THE APP

The app can be installed on a standalone Splunk server, a Search Head or a Search Head Cluster. In a distributed environment do not install the app on Indexers; the app should only be installed on Search Head(s).


*****************************
*** THE REST OF THE STORY ***
*****************************

WHAT INFOSEC APP DOES

InfoSec app for Splunk is your starter security pack for Splunk. InfoSec app is designed to address the most common security use cases, including continuous monitoring and security investigations. InfoSec app also includes a number of advanced threat detection use cases. All of the components of InfoSec app can be easily expanded using free security resources available for Splunk like Security Essentials app for Splunk: https://splunkbase.splunk.com/app/3435


ADDITIONAL TECHNICAL DETAILS SO YOU KNOW HOW THE APP WORK

InfoSec app is designed to use only basic Splunk functionality so it is easier for you to make the app your own by modifying and adding content from other free Splunk resources like Splunk Security Essentials (https://splunkbase.splunk.com/app/3435/)

InfoSec app uses the following macros you can modify to better match your Splunk configuration:
- Splunk indexes with security data `infosec-indexes`. Default value: index="*"
- Splunk indexes with Windows log data `wineventlog-index`. Default value: index="*"

InfoSec app uses the following accelerated searches to accelerate reports that cannot use Accelerated Data Models:
- 360 by Account: scheduled to run at approximately 15 minutes past every hour
- 360 by Host: scheduled to run at approximately 30 minutes past every hour

InfoSec app uses KV Store lookups for user and host information. Lookups are infosec_users and infosec_hosts. You will need to populate the lookups with your user and host information. Investigation dashboards will show user and host information if it is available in the lookups. 

InfoSec app uses dark theme available starting with Splunk 7.2. The app is known to work on Splunk versions 6.6 and newer. If you run a pre-7.2 version of Splunk, InfoSec app will show regular light dashboard background. 




*********************
*** RELEASE NOTES ***
*********************
Version 1.7.0 - July 2021
- Officially supported as a Splunk built app


Version 1.6.4 - October 3, 2020
- Basic data quality checks and warnings added to Security Posture and Health dashboards
- Added detailed CIM data summary report to Health dashboard
- Switched to 'Change' CIM data model from deprecated 'Change Analysis' model 
- Added links to InfoSec App documentation 
- Added city and source information in Scanning Activity report on IDS/IPS dashboard
- Cosmetic changes to dashboards 
- Bug fixes


Version 1.5.3 - April 6, 2020
- VPN Access dashboard is added under Search > Experimental Dashboards (requires CIM compliant VPN data mapped to VPN dataset of Network Sessions data model and Sankey diagram visualization)
- Calculations of event counts on maps are fixed 
- Display limit of 10,000 events introduced in investigation dashboards for all events with host/user
- Updated Health dashboard to list optional Sankey diagram visualization, optional VPN data
- Shortened main menu item names to accommodate for lower resolution displays


Version 1.5.2 - December 9, 2019
- Reports are adjusted to better reflect fields extracted and not extracted by current Windows add-on
- Time axis is fixed for 360 reports on Security Posture dashboard
- Miscellaneous cosmetic fixes


Version 1.5.0 - November 1, 2019
- Added infosec_hosts and infosec_user lookups; the lookups provide additional user and host information on investigation dashboards
- Search > Lookups menu item is added and links to users and hosts lookups (requires Lookup Editor app: https://splunkbase.splunk.com/app/1724/)  
- Network Traffic dashboard is split into Firewall and Network Traffic dashboards
- Pannel showing installed required add-ons is added to Health and Stats dashboard
- Over 15 pannels are added to dashboards under Continuous Monitoring and Advanced Threats
- Web CIM data model must be accelerated to display next gen firewall and/or web proxy data in Top Blocked Traffic Categories panel


Version 1.4.0 - April 12, 2019
- InfoSec Stats dashboard renamed to Health and Stats; the dashboard now shows count of events for each data model used by the app
- New app menu item Search > Experimental Dashboards
- New experimental Endpoints dashboard under Search > Experimental Dashboards(requires endpoint data to be sent to Splunk)
- Existing experimental Cloud Security dashboard is linked under Search > Experimental Dashboards (requires AWS data to be sent to Splunk)
- Intrusion Detection (IDS/IPS) dashboard: can now filter by allowed/blocked intrusion attempts
- Network Traffic dashboard > Network Communication Map: can now filter properly if network traffic app name has backslashes
- Several dashboards have references to advanced functionality available in Splunk Enterprise Security
- Additional Resources dashboard: added security journey stages, reference to Splunk Enterprise Security
- Bug fixes


Version 1.3.2 - February 1, 2019
Bug fixes: 
- search for malware indicator on Security Posture dashboard;
- drilldowns on Compliance dashboard;
- app package manifest schema changed to v1.0.0 for compatibility with older Splunk Cloud versions


Version 1.3 - January 29, 2019
Improved and expanded capabilities of authentication and network communication maps and associated filters
Bug fixes


Version 1.2 - November 29, 2018
Compliance dashboard added
Bug fixes


Version 1.1.1 - October 25, 2018
Bug fixes


Version 1.1.0 - October 21, 2018
Added alerting dashboard


Version 1.0.0 - October 3, 2018
Initial release
