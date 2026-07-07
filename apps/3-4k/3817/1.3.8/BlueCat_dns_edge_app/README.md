### OVERVIEW

#### About BlueCat DNS Edge for Splunk

| Author | BlueCat          |
| --- |------------------|
| App Version | 1.3.8            |
| Vendor Products | BlueCat DNS Edge |
| Has index-time operations | false            |
| Create an index | false            |
| Implements summarization | false            |

The BlueCat DNS Edge for Splunk app provides basic visualizations and alerts for BlueCat DNS Edge API data. This app is intended to work with data provided by the BlueCat DNS Edge Technical Add-on for Splunk modular input (link). This app provides a simple search interface and alert framework for DNS administrators and security professionals to review, monitor, and alert on policy events from their BlueCat DNS Edge service points.

##### Scripts and binaries

No scripts or binaries included.

#### Release notes

##### About this release

Version 1.3.8 of BlueCat DNS Edge for Splunk is compatible with:

| Splunk Enterprise versions | 7.0 & 8.0 & 8.1 & 8.2 & 8.3 & 8.4 & 9.0 & 9.1 |
| --- |--------------------------------------------------|
| CIM | 4.9.1 |
| Platforms | Platform independent |
| Vendor Products | BlueCat DNS Edge |
| Lookup file changes | Initial lookup creation |

##### New features

BlueCat DNS Edge for Splunk includes the following new features:

- Added "Query Protocol" and "DRS ID" data columns to policy events

##### Fixed issues

Version 1.3.8 of BlueCat DNS Edge for Splunk fixes the following issues:

- N/A

##### Known issues

Version 1.3.8 of BlueCat DNS Edge for Splunk has the following known issues:

- N/A initial release

##### Third-party software attributions

Version 1.3.8 of BlueCat DNS Edge for Splunk incorporates the following third-party software or libraries.

- N/A

#### Performance benchmarks

BlueCat DNS Edge for Splunk has been tested on standalone Splunk instances that meet the minimum reference hardware specifications. Impact of search queries varies depending on amount of policy events being collected and time range searched over.

##### Support and resources

**Questions and answers**

General Splunk troubleshooting advice can be found on answers.splunk.com

**Support**

Please contact edge-splunk@bluecatnetworks.com for support.


## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

BlueCat DNS Edge for Splunk can be installed on any server that meets the Splunk reference hardware specifications.

#### Software requirements

BlueCat DNS Edge for Splunk does not require any additional software.

#### Splunk Enterprise system requirements

Because this app runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Download

Download BlueCat DNS Edge for Splunk from [Splunkbase](https://splunkbase.splunk.com)

#### Installation steps

BlueCat DNS Edge for Splunk is only required on Splunk Search Heads and should be installed alongside the BlueCat DNS Edge Technical Add-on for Splunk. BlueCat DNS Edge for Splunk relies on data collected by the BlueCat DNS Edge Technical Add-on for Splunk. Install the TA as per the included instructions, configure inputs, and verify data is flowing into Splunk successfully before using this app.

To install and configure this app on your Splunk Search Head, follow these steps:

1. Download BlueCat DNS Edge for Splunk from Splunkbase.
2. Login to Splunk with an administrator account (default: admin).
3. Click the "Apps" dropdown in the upper left corner of the screen and select "Manage Apps".
4. Select "Install app from file", click "Choose file", navigate to the app package downloaded in the previous step, and click "Upload".
5. Splunk must be restarted to reload app icons, otherwise the app is completely functional without a restart.

## USER GUIDE

Return to the Splunk Home page and select "BlueCat DNS Edge for Splunk". On this page you can review Policy Event details. The "Policies" dropdown will not work until there is Policy Detail data and a lookup has been generated. To generate a Policy Details lookup table quickly, simply visit the "Policy Details" page. On this page you can review details about individual policies.

On the Policy Alerts page, users can select policy events they wish to be alerted about. Select a policy, select whether to enable or disable the policy, and click Submit. To modify the settings for this alert, navigate to Settings > Searches, Reports, and Alerts > BlueCat DNS Edge - Policy Alerts. There users can configure alert actions (email, ticket, scripts, etc.) and modify the alert schedule.


### Data types

This app is used to analyze data collected with the BlueCat DNS Edge Technical Add-on for Splunk. Knowledge objects for BlueCat DNS Edge data are defined in the technical add-on which should also be installed on the saerch head.

### Lookups

BlueCat DNS Edge for Splunk contains 2 lookup files.

** Lookupname**

bluecat_dns_edge_policies - A table of policies defined on BlueCat DNS Edge service points.

bluecat_dns_edge_policy_alerts - A table of policies defining which will actively be alerted on by Splunk.

### Configure BlueCat DNS Edge for Splunk

After selecting which policies to alert on, make sure to enable the saved search BlueCat DNS Edge - Policy Alerts in the Searches, Reports, and Alerts menu.

### Troubleshoot BlueCat DNS Edge for Splunk

Verify the lookup table bluecat_dns_edge_policy_alerts.csv has active alerts (the "Alerts" column will say "Active" for a given policy) - | inputlookup bluecat_dns_edge_policy_alerts

Verify the Saved Search "BlueCat DNS Edge - Policy Alerts" is enabled

Verify email settings are configured on this Splunk server and the "BlueCat DNS Edge - Policy Alerts" search is configured with email as an alert action

### Upgrade BlueCat DNS Edge for Splunk
Simply follow the same steps listed in "Installation Steps" but make sure the checkbox for "upgrade" is selected.

### Example Use Case ###

Search for DNS policy events on the "Policy Events" dashboard (e.g. DNS events from specific sources)
Receive email alerts for specific policy event triggers (e.g. blacklisted domains).
