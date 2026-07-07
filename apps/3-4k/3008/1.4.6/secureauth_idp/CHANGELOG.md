# Change Log

# Version
1.4.6

## Date
Oct 2022

## Changes
### Bug Fixes
- Fix issues on Overview and Login Activity Dashboards with API only logins
- Default to dark dashboards

# Version
1.4.5

## Date
Sep 2022

## Changes
### Bug Fixes
- Fix macro issues and setup more variables

# Version
1.4.4

## Date
May 2022

## Changes
### Bug Fixes
- Log messages, most specifically with API calls, are not the same between SYSLOG and flat log files (e.g., forwarded via Splunk Universal Forwarder)

# Version
1.4.3

## Date
May 2022

## Changes
### Bug Fixes
- Update queries for version 19.x and beyond and new EventIDs and other search parameters
- Fix Failed Password panel on Login Failures to account for UserPassword
- Modify default/props.conf - change ?P to ? for the field extractions
- Update logos
- Re-enable ua-parser and sankey diagrams
- Updated dashboards to version 1.1
- Fix API macros for newer versions

### General
- Submitted to App Inspect for Splunk Cloud -- no failures

# Version
1.3

## Date
January 2020

## Changes
### Bug Fixes
- Modify multiple dashboards that were not looking for the X-MS-Forwarded-Client-IP as the source IP address for WS-Trust logins

### Base Application
- Make modifications to code (removing demo data and Splunk AppInspect findings) to prepare for Splunk Cloud certification
- Update third-party libraries and remove any libraries that are no longer required
- Modify locally created code to be Python 3 compatible
- Update icons for new SecureAuth branding
- Add new lookups [eventID_class] and [eventID_definition]
- Remove sample event logs - contact your SecureAuth Sales Representative to get data for testing

### Dashboards
- Fix multiple bugs in existing dashboards for missing WS Trust Source IP and other query syntax

### Macros
- Modify macros to be version 9.0 and greater compatible and modify syntax to improve performance and rename IAW macro naming standards
