Release Notes
-------------
3.0.0 - 7/11/2025
  * Updated for use with Splunk 9.2 and later.
  * Remove javascript and CSS files to make it Cloud Ready.
  * Removed TA dependency to simplify the app.
  * Removed setup.xml to make it Cloud Ready
  * Instructions to customize macros for your environment without setup xml:
      Go to Settings → Advanced Search → Search macros.
      Select the Digital Guardian.
      Click Edit next to macro [index_macro]
      Enter your preferred value (e.g., your index name).
      Click Save.
      Repeat the process for other macros :[process_sourcetype], [events_sourcetype], [alerts_sourcetype]

-------------
2.0.3 - 2/8/2018
* Removed extra javascript
* Fixed file permissions

2.0.2 - 1/10/2018
* Updated for Splunk Cloud compatibility

2.0.0 - 2/10/2017
* Updated for use with Splunk 6.5 and later.
* Can be used with Splunk 6.4.x, but backward compatibility before that is not guaranteed.
* Bug Fixes

1.3.0 - 5/27/2015
* Moved lookups to TA
* Added Investigation Page
* Added Email and NTU pages
* Bug Fixes

1.2.5 - 1/15/2015
* Fixed issue with Drive Type Lookups
* Fixed issue with Data Egress Page related to Event Types

1.2.4 - 12/24/2014
* Fixed issue with Network Direction Lookup

1.2.3 - 12/24/2014
* Fixed issue with extensions search on events page for new chart includes
* Fixed base search to allow extension includes
* Backslash escaping to allow for better drilldowns.

1.2.2 - 12/23/204
* Fixed issue with base search for new charts on events page.

1.2.1 - 12/22/2014
* Fixed issue with Wildcard search changing search button name on click
* Fixed rendering issue with new charts on events page.
* Added Computer Type Lookup to application

Introduction
------------
This is version 3.0.0 of the Splunk Application to get insight from your Digital Guardian implementation.

Installation
------------
see the Fortra's Documentation for installing an app.

Usage
-----
Digital Guardian offers security’s most technologically advanced endpoint agent. Only Digital Guardian ends data theft by protecting sensitive data from skilled insiders and persistent outside attackers.

The Digital Guardian App for Splunk Enterprise lets customers understand risks to sensitive data across the enterprise from insider and outsider threats and respond appropriately. Users can improve incident response and investigation times by leveraging Splunk’s enterprise search capabilities across Digital Guardian event and alert data. The App includes an Add-on which brings Digital Guardian events and alerts into Splunk Enterprise.  The Add-on is designed for Digital Guardian 7.0.0 and above.  For use with previous versions please contact Digital Guardian.

The Digital Guardian App for Splunk Enterprise includes ten dashboards that visualize Digital Guardian events and alerts with advanced abilities to drill down and filter data to pinpoint threats, investigate and respond. Dashboards include:

• Data Classification: Show that sensitive data is effectively identified and classified
• Alerts: Monitor policy violations, validate appropriate controls are in place and provide input into incident response process
• Events: Monitor data leaving the enterprise by channel - Email, Print, Removable Devices and Network Uploads. Understand channel usage to establish risk level.
• Process: Monitor process (application) access to data and identify anomalies
• Data Egress: Monitor data movement to understand how and where data is put at risk to improve classification and controls
• Email: Monitor e-mail usage to understand how and where data is put at risk to improve classification and controls
• NTU: Monitor network traffic to understand how and where data is put at risk to improve classification and controls
• Advanced Threat Detection: Monitor malware alerts resulting from behavioral detection rules in Digital Guardian’s advanced threat module
• Operations: Monitor operations of the Digital Guardian IT infrastructure
• Investigation: Monitor alerts and processes in order to quickly identify risks


