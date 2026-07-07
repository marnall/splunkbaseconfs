# Remote Work Insights - Executive Dashboard

The purpose of the **Remote Work Insights - Executive Dashboard** is to provide the ability to aggregate information across VPN, authentication, and video conferencing services to provide insights into the connectivity, productivity, and engagement across a remote workforce.

## App Prerequisites
- Splunk Enterprise or Splunk Cloud v7.1.0+
- [Splunk Common Information Model (CIM)](https://splunkbase.splunk.com/app/1621/) v4.0.0+
- [Splunk Add-on for RWI - Executive Dashboard](https://splunkbase.splunk.com/apps/id/Splunk_SA_rwi-executive-dashboard) v1.0.0+

## Upgrade RWI - Executive Dashboard from v1.0.x to v.1.1.x
1. Backup any custom dashboards or reports that were created while on v1.0.x
2. Backup the navigation bar (default.xml), only if you have modified the application menu bar
3. Download and install the latest version of the [Splunk Add-on for RWI - Executive Dashboard](https://splunkbase.splunk.com/apps/id/Splunk_SA_rwi-executive-dashboard) from Splunkbase
    * *Installing on Splunk Cloud*: Installing on Splunk Cloud through Self-Service Apps Install requires Splunk Cloud version 7.1.x or later.
    * To install on *Splunk Cloud version 7.0.x or earlier*, submit a case to Splunk Support. See Contact Splunk Support for contact information and how to submit a case.
4. Download and install the latest version of the [RWI - Executive Dashboard](https://splunkbase.splunk.com/app/4952)
    * *Installing on Splunk Cloud*: Installing on Splunk Cloud through Self-Service Apps Install requires Splunk Cloud version 7.1.x or later.
    * To install on *Splunk Cloud version 7.0.x or earlier*, submit a case to Splunk Support. See Contact Splunk Support for contact information and how to submit a case.
5. Restart the *Splunk Search Head* or Initiate a *Search Head Cluster* Rolling Restart
6. Access the RWI - Executive Dashboard app v1.1.x+ for the first time using a Splunk Admin account and proceed with the Guided Setup
    * App Prerequisites check
    * Indexes macros configuration
    * Data collections check
    * Features/Navigation bar configuration
7. Restore any custom dashboards or reports from Step 1
8. ** **See Important Note Before Proceeding** **
9. Merge any custom navigation menu from Step 2 with the default navigation bar. 

## Important Note

### Navigation Menu
- If you have modified the Navigation Bar, you may still use the **Guided Setup**. Though, the menu ordering of the navigation bar may changes.
- If you are upgrading from v1.0 to v1.1, you may access the Guided Setup using this link: `http(s)://<your_splunk_hostname>:<port>/en-US/app/rwi_executive_dashboard/guided_setup`

### Configure Indexes Macros
The Indexes Macros were moved to the [Splunk Add-on for RWI - Executive Dashboard](https://splunkbase.splunk.com/apps/id/Splunk_SA_rwi-executive-dashboard). You may still configure the Indexes Macros outside of the *Guided Setup* : 

1. From the Splunk Search Head, Go to **Settings > Advanced Search > Search Macros** to update the Indexes Macros
2. Update the indexes macro with your index(es). 
3. Example Configuration: *(index=vpn)*
4. Macro Name:
     1. **Authentication**: *rw_auth_indexes* 
     2. **Video Conferencing**: *rw_vc_indexes* 
     3. **VPN**: *rw_vpn_indexes*

## Release Notes

### Version 1.1.2 - August 20, 2020
- Updated app.manifest: Removed dependencies to unblock Splunk Cloud Self-Service Installation upgrades from 1.0.x to 1.1.x
- Updated rw_vpn_gp_logins.xml: fix panels to use the time token

### Version 1.1.1 - June 15, 2020
- Updated app.manifest

### Version 1.1.0 - June 15, 2020
- Included a **Guided Setup** to assist with the App configuration. This new feature is dependant on the [Splunk Add-on for RWI - Executive Dashboard](https://splunkbase.splunk.com/apps/id/Splunk_SA_rwi-executive-dashboard).
  - App Prerequisites check
  - Indexes macros configuration
  - Data collections check
  - Features/Navigation bar configuration
- Updated the **Video Conferencing SPL searches** to leverage the Video Conferencing Data Model from the [Splunk Add-on for RWI - Executive Dashboard](https://splunkbase.splunk.com/apps/id/Splunk_SA_rwi-executive-dashboard).
- **Video Conferencing Ops Dashboard** to support the Cisco Webex Meetings, Microsoft Teams and Zoom data collected by the following connector:
  - [Cisco WebEx Meetings Add-on for Splunk](https://splunkbase.splunk.com/app/4991)
  - [Microsoft Teams Add-on for Splunk](https://splunkbase.splunk.com/app/4994)
  - [Splunk Connect for Zoom](https://splunkbase.splunk.com/app/4961/)
- App icon updated

### Version 1.0.4 - April 15, 2020
- Splunkbase Official Release

## Third-party software attributions/credits
Some of the components included in **RWI - Executive Dashboard** are licensed under free or open source licenses. View the license(s) associated with each component in [CREDITS.md](CREDITS.md).

## License
Code licensed under [Apache 2.0](http://www.apache.org/licenses/LICENSE-2.0.html). All non-text documentation provided herein, including screenshots, logos and images, are provided for reference only and remain the property of Splunk or its licensors.
