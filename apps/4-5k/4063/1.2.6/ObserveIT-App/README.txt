ObserveIT App for Splunk provides dashboards and data models for analyzing 
ObserveIT (tm) alerts and users sessions data
The app relies on data collected by ObserveIT Add-on for Splunk

RELEASE NOTES
Version 1.0.0 
 * Released: June-2018

Version 1.2.4
 * Updated for jQuery 3.5 compatibility
 * Fixed minor rendering errors

Version 1.2.6
 * Bumping version to comply with Splunk's new archiving policy
 
INSTALLATION AND CONFIGURATION

REQUIREMENTS
- Hardware Requirements:
  Refer to System Requirements document
  http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements

- Software Requirements:
  1. Splunk Enterprise v6.5+ or Splunk Cloud 
  2. ObserveIT Add-on for Splunk v1.0+ for data collection

INSTALLATION INSTRUCTIONS
Refer to Splunk Documentation
http://docs.splunk.com/Documentation/Splunk/latest/Admin/Deployappsandadd-ons

- Installing the app in a distributed Splunk Enterprise deployment
  The app should be installed on Search Heads only.

FEATURES
- Dashboards
  * Alerts Dashboard
    The alerts dashboard shows the top alerts and top risky users and 
    applications. All alerts are listed, with a link to launch the ObserveIT 
    player to playback the user's session. The session column lets you drill 
	down to the individual activities that made up the alerted session.

  * User Sessions Dashboard
    The user session dashboard shows most active users and endpoints as well as 
    the most used applications. An overview summary of each user session is 
    available, including the start and end time of the session, the number of 
    unique activities, and the user involved. A link to the ObserveIT player to 
    replay the session is also included. A drilldown will show more details 
	about individual activities that make up the session.

PERFORMANCE
This App contains a data model with two datasets representing alerts and users 
sessions. 
It is recommended to accelerate the data model and limit datasets base searches
to indexes containing data collected by ObserveIT TA for Splunk

SUPPORT
For support configuring or using the ObserveIT App for Splunk, please contact 
us at integrations@observeit.com. Support is provided during weekday business 
hours (US, West Coast)

For help using the ObserveIT platform, please contact the ObserveIT support 
organization. https://www.observeit.com/support/

LICENSE
ObserveIT App for Splunk is provided under Apache License version 2.0
