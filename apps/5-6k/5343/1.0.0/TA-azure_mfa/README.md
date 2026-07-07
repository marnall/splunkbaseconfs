## Microsoft Azure On-Premise MFA Add-on for Splunk

* Add-on Homepage: https://apps.splunk.com/apps/id/TA-azure_mfa
* Author: Hurricane Labs
* Version: 1.0.0

## Description
The purpose of this add-on is to provide value to your Microsoft Azure On-Premise MFA (previously PhoneFactor) logs. This is done by making the logs CIM compliant, adding tagging for Enterprise Security data models, and other knowledge objects to make searching and visualizing this data easy.

* Supports:
  * Syslog
  * MultiFactorAuthAdSyncSvc.txt
  * MultiFactorAuthLdapSvc.txt
  * MultiFactorAuthRadiusSvc.txt
  * MultiFactorAuthSvc.log.txt
* Built for Splunk Enterprise 6.x.x or higher
* CIM Compliant (CIM 4.0.0 or higher)
* Ready for Enterprise Security

## Constraints
1. This add-on requires that you use the sourcetype "ms:mfa" when ingesting the data.
2. This add-on must be installed on your Search Head(s).
3. This add-on is ONLY for On-Premise MFA. If you're looking for Azure MFA Cloud logs, use this add-on: https://splunkbase.splunk.com/app/3757/

## Azure MFA Logging Settings
1. Login to your MFA server with admin credentials
2. Search for 'multi-factor authentication server management' and open it.
3. Go to "Logging" and configure the options as you'd prefer (either Logging on disk or Syslog is acceptable.)
* Note: Default logging path on disk is "C:\Program Files\Multi-Factor Authentication Server\Logs"

## SPLUNK INSTALLATION AND CONFIGURATION
* Search Head: Add-on Always Required (Knowledge Objects)
* SH & Indexer Clustering: Supported

### Add-on Installation Instructions
1. Install the add-on on your Search Head(s).
2. If you installed via CLI, you will need to run a debug/refresh or restart Splunk. If you install via GUI, nothing else is required.
3. Verify data is coming in and you are seeing the proper field extractions by searching the data.
    * Example Search: index=azure sourcetype=ms:mfa
4. (Optional, recommended) On your Search Head(s) edit the "azure_mfa_auth" and "azure_mfa_auth" Event Types to include the index you're storing this sourcetype in.

### New features
* 1.0.0: Add-on Released

### Fixed issues

### Known issues

### Third-party software attributions

### DEV SUPPORT
Contact: splunk-app@hurricanelabs.com
