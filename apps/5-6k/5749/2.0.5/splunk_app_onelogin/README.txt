OneLogin App for Splunk
Splunk Version: 9.3.0 and Higher
App Version:    2.0.5
Last Modified:  December 2024
Authors:        OneLogin, Inc.
Contacts:       support@onelogin.com

The OneLogin App for Splunk allows a Splunk® software administrator to collect data from OneLogin server. App has a prebuild dashboards with basic information. It includes:
- GEO map of all events
- Logins by country
- Count of users and applications
- Provisioning errors
- Failed logins and password resets
- Assumed logins
- Provisioning/failed provisioning/user creation count per application

App requires OneLogin Add-on for Splunk.

Documentation

Introduction:

Onelogin user can capture valuable information through API from Onelogin database over time. This app collects events such as signing in, provisioning, user creating, count of users and applications, geolocations, etc.

Out-of-the-box dashboard provides information about users and applications count, basic provisioning data and provisioning errors, geo map of all events. Also, dashboard has dropdown with datetime. You can change period of the information showing by setting date and/or time in that dropdown.

Installation and Configuration:

1. Install the OneLogin Add-on for Splunk and configure it by following the add-on documentation

2. Install OneLogin App for Splunk

Frequently Asked Questions:

Q: Does Onelogin API key belong to specific user?

A: No. API key is connected to the account, which has many users and applications. So when you add API key, Splunk will grab all events from all users in that specific account.

Q: How much time does it take Splunk to index all events from Onelogin?

A: It depends on how much user you have and them activity. Splunk indexes by 50 events at the time. So if you have couple of milions different actions in your account, it takes time. Also Splunk starts indexing from the oldest events, so you will see old information at first and indexing proceeds in the background to catch new data.
