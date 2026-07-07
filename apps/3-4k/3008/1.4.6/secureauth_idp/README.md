# Information

App: SecureAuth Identity Platform
Current Version: 1.4.6
Last Modified: October 2022
Splunk Version: 22.x/21.x/20.x/19.x/9.x
Author: SecureAuth Corporation

# Overview

SecureAuth IdP for Splunk provides a clear view of user access into your enterprise resources such as VPN and ADC, cloud application access as well as on-premise applications.  All teams in your organization will be able to leverage the dashboards, such as Security teams for suspicious activity and forensics, Operations for health, load and response times, Application teams for application access history and trends, as well as C-Level reporting for management.

The SecureAuth IdP Splunk App supports SecureAuth IdP version 9.0 and greater through syslog datasets. Please contact your Sales Representative if you need support for an IdP version prior to 9.0.

# Quick Start Guide

Required Plugins:

- Sankey Diagram: https://splunkbase.splunk.com/app/3112/
- TA-User-Agents: https://splunkbase.splunk.com/app/1843/

Install the app:

There are three ways to install the app:

1.  Install from Splunk web UI:
	- Manage Apps -> Browse more apps -> Search keyword 'SecureAuth' -> Click Install free button -> Click to restart Splunk service.


2.	Install from file on Splunk web UI:
  - Download the SecureAuth IdP Splunk App from https://splunkbase.splunk.com/app/3008
	- Install via: Manage Apps -> Install from file -> Upload the downloaded .tgz file -> Click to restart Splunk service.


3.	Install from file on Splunk server CLI interface:
	- Download the SecureAuth IdP Splunk App from https://splunkbase.splunk.com/app/3008
	- Change directory to $SPLUNK_HOME/etc/apps -> Extract the .tgz file (`sudo tar zxvf <location_of_tgz_file>`) -> Restart Splunk service (`sudo $SPLUNK_HOME/bin/splunk restart`).

# App Configuration
## Index
Due to recent changes by Splunk, you will need to make your own index for the data. You can simple copy the "indexes.conf.sample" from the default folder into the local folder and rename it to "indexes.conf".

By default this app assumes your data will be located in index="secureauth".

You can update all of the dashboards by simply modifying the [secureauth_base] stanza in "macros.conf".

## Sourcetype
This app requires the sourcetype "secureauth:idp" to render all dashboards.

You can either rename your existing sourcetype by going to "Settings -> Fields -> Sourcetype renaming" or update the props.conf to match your existing sourcetype.

## Demo Data
The app no longer contains demo data.

If you would like to install demo data, please contact your Sales Representative.

# Third Party Library References

Third Party Libraries are no longer used in the app.

# Release Notes
1.4.6: October 2022
	- Fix issues on Overview and Login Activity Dashboards with API only logins
	- Default to dark dashboards

1.4.5: September 2022
	- Fix macro issues and setup more variables

1.4.4: May 2022
	- Log messages, most specifically with API calls, are not the same between SYSLOG and flat log files (e.g., forwarded via Splunk Universal Forwarder)

1.4.3: May 2022
	- Fix API macros for new logging messages

1.4.2: April 2022
	- Remove unused python packages

1.4.1: April 2022
	- Fix Dashboards to version=1.1

1.4.0: September 2021
	- Update logos
	- Re-enable sankey diagrams and User Agents
	- Require Sankey and TA-user-agents from Splunkbase
	- Restore user-id and src-ip search fields
	- Create all-logins dashboard
	- Update various queries for Identity Platform 19.x and beyond

1.3.0: December 2019
	- See CHANGELOG.md for details

1.2.18317: July 2018
	- Update for new Splunkbase compliance rules

1.2.19169: June 2018
	- Update for new Splunkbase compliance rules

1.2.19136: June 2018
	- Update for new Splunkbase compliance rules

1.1.17262: September 2017
	- Configuration cleanup
	- Change versioning format per new Splunk guidlines

v16350.1: December 2016
	- Removed indexes.conf per Splunk's app certification changes.

v16195.1: July 2016
	- Removed deprecated XML

v16147.1: May 2016
	- Added parens to macro queries to fix logic
	- Added WS transactions to login_activity screen

v16127.1: April 2016
	- Added API dashboard
	- Added Behavior API panels
	- Corrected issue where some logon events were not captured
	- Corrected issue where response times were not accurate

v16062.1: March 2016
  - Updated dashboards for new terminology

v16056.1: February 2016
	- Updated dashboards for new terminology

v16054.1: February 2016
	- Updated dashboards to use new threat feed

v16035.1: February 2016
	- Query fixes around the credential provider

v16026.2: January 2016
	- Eventgen bug fixes
	- Fixed report typo
	- Fixed various query criteria

v16019.1: December 2015
- Initial release
