# OVERVIEW

The Agari App for Splunk collects alerts from Agari Brand Protection, and events from Agari Phishing Defense and Agari Phishing Response products and allows you to view and query them from within your Splunk instance. These real-time alerts include Threat Spikes, Brand Spoofing, Authentication Spikes, Infrastructure Alerts, DMARC and SPF Record Changes, and New Sender notifications. The events from Phishing Defense and Phishing Response will include policy, messages, and investigations.


# REQUIREMENTS

- Agari Add-on For Splunk
- Splunk version 8.X.X
- This application should be installed on Search Head


# Release Notes

## Version: 3.0.0

- Separation of TA & App
- Support for Splunk Cloud
- Dashboards for Agari Brand Protection

## Version: 3.1.0

- Added Support for Agari Phishing Defense
- Added support for additional Alert types in Agari Brand Protection
- Minor bug fixes

## Version: 3.1.1

- Minor Bug Fixes

## Version: 3.1.2

- Minor update in query

## Version: 3.2.0

- Added Support for Agari Phishing Response
- Updated jQuery 3.5 version


# RECOMMENDED SYSTEM CONFIGURATION

- Standard Splunk configuration of Search Head.

# Test your Install

The main app dashboard can take some time before the data is returned which will populate some of the panels. A good test is to run the following query:

`` search `macro_main_agari`  ``

If you don't see the data yet available after few minutes, try running the below query to see if there are any errors:

`index="_internal"`

# Support

Additional support for this application is available at the following URL:
https://agari.zendesk.com/hc/en-us/articles/115001959803
