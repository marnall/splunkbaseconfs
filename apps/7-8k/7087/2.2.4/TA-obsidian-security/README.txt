Obsidian Security Splunk App
Copyright Obsidian Security, Inc, 2020-present
support@obsidiansecurity.com


- INTRODUCTION -
This Splunk App is a way for security teams to integrate Obsidian's Cloud
Detection and Response solution into a Splunk deployment.

This app reaches out to Obsidian's API via HTTPS/443, optionally using a
web proxy, to request the data related to the inputs that have been enabled.


- INSTALLATION OVERVIEW -
The app can be configured with multiple inputs. Each input requires an API
token, time interval (in seconds), subdomain, and other optional fields.

Once an input is installed, the app will reach out to the Obsidian GraphQL
API at the specified interval and will pull any data that is more recent
than the last fetch. The data is then stored in Splunk and searchable as
well as reflected in the Obsidian Security Splunk App Dashboard.


- OBSIDIAN ALERTS -
The Obsidian Alerts input will retrieve Obsidian alerts that have fired
as well as optionally the related events for such alerts. This should
largely be the same information as the "Alerts" page in the Obsidian
product.

-- Setup --
To setup an Obsidian Alerts input, you'll need to fill out the following
fields:

Name: <name to call the input, i.e. obsidian_alerts
Interval: <number of seconds >= 60 between fetch attempts>
Index: <your desired Splunk index>
API Token: <your API Token; "Settings" -> "API Access tokens" in Obsidian>
Subdomain: <your tenant subdomain, "acme" for acme.obsec.io>
Alert Query: <query to filter alerts same as on "Alerts" page>
Fetch Related Events: <enable fetching Obsidian events related to the alerts>
Proxy Setting: <set a proxy url if required, i.e. http://127.0.0.1:8080>


-- Searching --
Events can be searched through normal splunk searching by searching for:
sourcetype="obsidian:alerts"


- OBSIDIAN EVENTS -
The Obsidian Alerts input will retrieve Obsidian events that have been
collected by the Obsidian product. This is similar to the "Activity"
page in the Obsidian product.


-- Setup --
To setup an Obsidian Events input, you'll need to fill out the following
fields:

Name: <name to call the input, i.e. obsidian_alerts
Interval: <number of seconds >= 60 between fetch attempts>
Index: <your desired Splunk index>
API Token: <your API Token; "Settings" -> "API Access tokens" in Obsidian>
Subdomain: <your tenant subdomain, "acme" for acme.obsec.io>
Event Query: <query to filter events same as on "Events" page>
Proxy Setting: <set a proxy url if required, i.e. http://127.0.0.1:8080>


-- Searching --
Events can be searched through normal splunk searching by searching for:
sourcetype="obsidian:events"


- DASHBOARD -
There is an Obsidian Security Splunk Dashboard that should be the primary
page you see when visiting the app. The queries can be customized to your
environment and preferences.


- TROUBLESHOOTING -
Logging is enabled and should be stored in:
%SPLUNK_HOME%/var/log/splunk/ta_obsidian_security_obsidian_*.log


================================================================================
RELEASE NOTES - Obsidian Security Splunk Technical Add-on
================================================================================

OVERVIEW

The Obsidian Security Splunk Technical Add-on (TA-obsidian-security) enables 
security teams to integrate Obsidian's Cloud Detection and Response solution 
into their Splunk deployment. This add-on provides real-time ingestion of 
security alerts and events from the Obsidian platform.

--------------------------------------------------------------------------------

Version 2.2.4 (Current)
Release Date: Feb 17, 2026

CHANGES:
- Bug fix for posture violation datetime formatting.
--------------------------------------------------------------------------------

Version 2.2.3
Release Date: Feb 6, 2026

CHANGES:
- Bug fix for handling high event volume of obsidian events.
--------------------------------------------------------------------------------

Version 2.2.2
Release Date: Feb 3, 2026

CHANGES:
- Added rule_id field to posture violations for easier rule lookup.
--------------------------------------------------------------------------------

Version 2.2.1
Release Date: Jan 26, 2026

CHANGES:
- Updating posture violations input API.
--------------------------------------------------------------------------------

Version 2.2.0
Release Date: Jan 23, 2026

CHANGES:
- Added input for Alerts triage by identity.
- Updated dashboard with 'Alerts triage by identity' panel
- Fix obsidian event query filter issue.
--------------------------------------------------------------------------------

Version 2.1.1
Release Date: Dec 5, 2025

CHANGES:
- Fixing the token subdomain name validation issue for IR tenants.
--------------------------------------------------------------------------------

Version 2.1.0
Release Date: Nov 10, 2025

CHANGES:
- Added inputs for posture data, including rules, settings, and violations.
--------------------------------------------------------------------------------

Version 2.0.2
Release Date: Nov 7, 2025

CHANGES:
- Added configurable throttling parameters for obsidian events:
  * time_window_seconds: Defines the default time window (in seconds) for event fetching during each polling cycle. (default: 7200, minimum: 1800)
  * min_time_window_seconds: Specifies the minimum allowable time window (in seconds) for event fetching. (default: 60, minimum: 2)
  * batch_size: Sets the number of events processed in each Obsidian graphQL call. (default: 500, range: 100-5000)
  * eps_threshold: Defines the target Events Per Second (EPS) threshold for Splunk indexing. (default: 100, minimum: 50)     

--------------------------------------------------------------------------------

Version 2.0.1
Release Date: October 17, 2025

CHANGES:
- introduces subdomain name validation when setting up inputs

--------------------------------------------------------------------------------

Version 2.0.0
Release Date: October 6, 2025

CHANGES:
- Addressed Splunk Cloud vetting warnings

--------------------------------------------------------------------------------

Version 1.4.6
Release Date: September 5, 2025

CHANGES:
- Adding alerts context for phishing alerts
- Fixing phishing alerts related activity events missing issue

--------------------------------------------------------------------------------

Version 1.4.5
Release Date: January 30, 2024

CHANGES:
- Upgrade TA Builder to 4.4.1 and related libs are upgraded as well, such as, 
  the solnlib library package to version 6.0.1, splunk SDK 2.1.0 etc.
- Added Max Retries configuration for setting up alert input to fetch related events.
- Fixed an issue with alert timestamp format inconsistency.
- Introduced an Initial Alert ID feature, allowing customers to resume alert 
  fetching from the last processed point after a reinstall.

--------------------------------------------------------------------------------

Version 1.4.4
Release Date: January 9, 2025

CHANGES:
- Upgraded the solnlib library package to version 4.12.0.
- Added Max Retries configuration for setting up alert input to fetch related events.
- Fixed an issue with alert timestamp format inconsistency.
- Introduced an Initial Alert ID feature, allowing customers to resume alert 
  fetching from the last processed point after a reinstall.

--------------------------------------------------------------------------------

Version 1.4.3
Release Date: December 13, 2024

CHANGES:
- Fix issue of upgrading failure because of collections.conf need to be in 
  default folder from version 1.3.0

--------------------------------------------------------------------------------

Version 1.4.2
Release Date: October 30, 2024

CHANGES:
- Fix the audit log event fields are extracted twice because of missing 
  configuration in props.conf

--------------------------------------------------------------------------------

Version 1.4.1
Release Date: October 23, 2024

CHANGES:
- Resolved the issue of alerting missing related activity events. For more 
  information, please refer to our official documentation.

--------------------------------------------------------------------------------

Version 1.4.0
Release Date: October 9, 2024

CHANGES:
- Get Obsidian audit log into Splunk as event type obsidian:audit

--------------------------------------------------------------------------------

Version 1.3.2
Release Date: September 4, 2024

CHANGES:
- Adding new API URI for the new Data center in Australia and Saudi Arabia
- Set alert TIMESTAMP_FIELDS to 'generated_datetime
- Fix some bugs

--------------------------------------------------------------------------------

Version 1.3.1
Release Date: May 28, 2024

CHANGES:
- Fixing KVStore checkpoint issue
- Changing to call get API version to validate input
- Adding more log info for debug purpose

--------------------------------------------------------------------------------

Version 1.3.0
Release Date: April 3, 2024

CHANGES:
- Support Obsidian Customers in Europe

--------------------------------------------------------------------------------

Version 1.2.2
Release Date: Feb 20, 2024

CHANGES:
- Added more fields (alert_extra_data and taxonomy) to alert event so that 
  customers could do alert triage easily.
- Fix a validation inputs default value issue.
- Fix package extraction issue on CentOS

--------------------------------------------------------------------------------

Version 1.2.1
Release Date: Dec 18, 2023

CHANGES:
- Upgrade Splunk SDK to 1.7.4
- Grant cloud 'sc_admin' write permission for knowledge objects

--------------------------------------------------------------------------------

Version 1.2.0
Release Date: November 28, 2023

CHANGES:
- Rebuilt the app with latest Splunk Add-on Builder and the app supports 
  Splunk Cloud Now.
- Tenant data is available now.

--------------------------------------------------------------------------------

Version 1.1.4
Release Date: November 20, 2023

CHANGES:
- Support Splunk Cloud

--------------------------------------------------------------------------------

Version 1.1.2
Release Date: October 24, 2023

CHANGES:
- Bundle public cert into the package to solve the REST API call fails at 
  cert verification.

--------------------------------------------------------------------------------

Version 1.1.0
Release Date: October 19, 2023

CHANGES:
- First version release in Splunkbase

--------------------------------------------------------------------------------

For technical support or feature requests, please contact the Obsidian 
Security team at support@obsidiansecurity.com

Copyright (c) 2020-present Obsidian Security, Inc. All rights reserved.

