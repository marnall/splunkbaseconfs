# Splunk Add-on for RWI - Executive Dashboard
This Splunk Add-on provides support functions to the **[RWI - Executive Dashboard](https://splunkbase.splunk.com/app/4952/)** v1.1+ as to data models, field search-time extractions for the views, reports provided in the main application.

## Prerequisites

Splunk Enterprise or Splunk Cloud 7.0 or Above

## Installation

This app is intended to work on Search Head Clusters, as well as single instance deployments in both Splunk Cloud, and On-Prem. There are no major considerations for installing Remote Work Insights - simply follow your usual Splunk App Deployment procedure. 

### Installing on Splunk Cloud

\*\* Installing on Splunk Cloud through Self-Service Apps Install requires Splunk Cloud version 7.1.x or later. \*\*

* Download the [Splunk Add-on for RWI - Executive Dashboard](https://splunkbase.splunk.com/apps/id/Splunk_SA_rwi-executive-dashboard)  in your Splunk Cloud Deployment from Splunkbase. See [Install apps in your Splunk Cloud deployment](http://docs.splunk.com/Documentation/SplunkCloud/latest/User/SelfServiceAppInstall) in the [Splunk Cloud User Manual](https://docs.splunk.com/Documentation/SplunkCloud/latest/User/WelcometoSplunkCloud) for further instructions.
* To install [Splunk Add-on for RWI - Executive Dashboard](https://splunkbase.splunk.com/apps/id/Splunk_SA_rwi-executive-dashboard)  on Splunk Cloud version 7.0.x or earlier, submit a case to Splunk Support. See [Contact Splunk Support](http://docs.splunk.com/Documentation/Splunk/latest/Troubleshooting/ContactSplunkSupport) for contact information and how to submit a case.

### Installing on a Stand Alone Search Head

1. Launch Splunk Enterprise.
2. Log in.
3. Download the [Splunk Add-on for RWI - Executive Dashboard](https://splunkbase.splunk.com/apps/id/Splunk_SA_rwi-executive-dashboard)  from Splunkbase.
4. Click the Apps gear icon in Splunk Enterprise.
5. Click _Install app from file_.
6. Click _Choose File_ and select the downloaded file.
7. Click **Upload**.
8. Restart Splunk Enterprise.

## Configure Indexes Macros

1. From the Splunk Search Head, Go to **Settings > Advanced Search > Search Macros** to update the Indexes Macros
2. Update the indexes macro with your index(es). 
3. Example Configuration: *(index=vpn)*
4. Macro Name:
     1. **Authentication**: *rw_auth_indexes* 
     2. **Video Conferencing**: *rw_vc_indexes* 
     3. **VPN**: *rw_vpn_indexes*

## Release Notes

### Version 1.0.1 - June 2020
- Official Release to Support the RWI - Executive Dashboard App 1.1.0+

## License
[Splunk General Terms](https://www.splunk.com/en_us/legal/splunk-general-terms.html)

Copyright (C) 2005-2020 Splunk Inc. All Rights Reserved.
