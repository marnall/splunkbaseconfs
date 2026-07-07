# Splunk App for Zoom

The Splunk App for Zoom provides the interface for searches, reports, and dashboards for your Zoom video conferencing environment. It works in concert with [Splunk Connect for Zoom](https://splunkbase.splunk.com/app/4961), which connects to your Zoom data, to enable you to monitor, manage, and troubleshoot your Zoom service from a single application.

## Release Notes

### Version 1.0.3 - August 5, 2022

-   jQuery upgrade: Set dashboards to version 1.1

### Version 1.0.2 - May 15, 2020

-   Fix SPL for the Meeting/Webinar Alerts

### Version 1.0.1 - April 15, 2020

-   GA Release

## Prerequisites

Splunk 7.0 or Above

## Installation

This **Splunk App for Zoom** is intended to work on Search Head Clusters, as well as single instance deployments in both Splunk Cloud, and On-Prem. It is used to visualize the Zoom data collected via the [Splunk Connect for Zoom](https://splunkbase.splunk.com/app/4961) connector.

Please be aware that this is the visualization app for Zoom data in Splunk. It does not cover data collection for Zoom. That can be achieved by referencing the [Splunk Connect for Zoom](https://splunkbase.splunk.com/app/4961) connector and its corresponding documentation.

There are some minor configuration steps you may need to do with this app in order for it to work in your environment. They are listed in the **Configuration** section.

### Installing on Splunk Cloud

** Installing on Splunk Cloud through Self-Service Apps Install requires Splunk Cloud version 7.1.x or later. **

See [Install apps in your Splunk Cloud deployment](http://docs.splunk.com/Documentation/SplunkCloud/latest/User/SelfServiceAppInstall) in the [Splunk Cloud User Manual](https://docs.splunk.com/Documentation/SplunkCloud/latest/User/WelcometoSplunkCloud) for further instructions.

To install Splunk App for Zoom on Splunk Cloud version 7.0.x or earlier, submit a case to Splunk Support. See [Contact Splunk Support](http://docs.splunk.com/Documentation/Splunk/latest/Troubleshooting/ContactSplunkSupport) for contact information and how to submit a case.

### Installing on a Stand Alone Search Head

1. Launch Splunk Enterprise.
2. Log in.
3. Download **Splunk App for Zoom** from Splunkbase.
4. Click the **Apps gear icon** in Splunk Enterprise.
5. Click **_Install app from file_**.
6. Click **_Choose File_** and select the downloaded file.
7. Click **Upload**.
8. **Restart** Splunk Enterprise.

## Configuration

### Configuring Zoom Index

1. From the Splunk Search Head, go to the **Splunk App for Zoom** App
2. Go to **_Settings > Advanced Search > Search Macros_** to update the Indexes Macros
3. Update the Zoom indexes macro with your index.
    - Macro Name: **zoom_indexes**
    - Example Configuration: `(index=zoom)`

## License

[Splunk General Terms](https://www.splunk.com/en_us/legal/splunk-general-terms.html)

Copyright (C) 2005-2020 Splunk Inc. All Rights Reserved.
