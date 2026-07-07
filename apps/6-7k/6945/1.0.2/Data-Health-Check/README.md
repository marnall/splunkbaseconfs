# Check-Your-Data
Instructions

Prerequisites

Install https://splunkbase.splunk.com/app/6368

Install

This app should be installed on Search Heads https://docs.splunk.com/Documentation/SplunkCloud/latest/Admin/Experience Install the app. For Splunk Cloud, refer to Install apps in your Splunk Cloud deployment. For customer managed deployments, refer to the standard methods for Splunk Add-on installs as documented for a Single Server Install or a Distributed Environment Install.

Configuration

Make sure you are a sc_admin or admin

Usage

Main Data Quality: 

This dashboard would assist you to troubleshoot any sourcetype.
You would get information from last 100 events and indextime data.

Event Parser: 

Use this dashboard to parse all your events.
Grab a sample log, paste the required information and confirm your data is following the Magic 8.

Video would be available soon...

Known Issues

See the release notes of the latest version for known issues

Troubleshooting Steps

If there are no events: 
1. Make sure you can search on the selected index.
2. Change the time range picker.

Upgrade

No special instructions for upgrading this app to a newer version.

Help
While this app is not formally supported, the developer can be reached at splunkbase@prudentconsulting.com. Responses are made on a best effort basis. Feedback is always welcome and appreciated! (if you use the User Group approach, include: Learn more about splunk-usergroups slack here: https://docs.splunk.com/Documentation/Community/current/community/Chat#Join_us_on_Slack)
