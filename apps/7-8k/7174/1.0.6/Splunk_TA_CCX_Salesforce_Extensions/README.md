**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Extensions for Salesforce looks to provide additional field extraction and CIM compliance for for Salesforce log sources captured via the Add-ons Splunk Add-on for Salesforce or Splunk Add-on for Salesforce Streaming API.

This Technical Add-on does not replace the public Splunk Add-on for for Salesforce (https://splunkbase.splunk.com/app/3549) or Splunk Add-on for Salesforce Streaming API (https://splunkbase.splunk.com/app/5689) but works as an additonal extension to be deployed on Search Heads (only).

Currently this add-on provides additional extraction and CIM compliance for sourcetypes:

- sfdc:loginhistory
- sfdc:setupaudittrail
- sfdc:logfile

- sfdc-streaming-api-events:login
- sfdc-streaming-api-events:report
- sfdc-streaming-api-events:security

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes for Splunk Add-on for Salesforce tagged under the following CIM datamodels: Alerts, Authentication, Change, Data Access, and Web

- This TA currently supports logtypes for Splunk Add-on for Salesforce Streaming API tagged under the following CIM datamodels: Alerts, Authentication, Data Access, and Instrusion Detection (IDS)

**Compatibility:**
| Splunk Enterprise versions | 10,9.4,9.3,9.2,9.1   |
| -------------------------- | -------------------- |
| CIM                        | 6.x, 5.x             |
| Platforms                  | Platform independent |
| Vendor Products            | Salesforce           |
| Service Provider           | CyberCX              |

**Requirements:**

- This add-on is intended to be installed on Splunk Search Heads as an extension to either Splunk Add-on for Salesforce or Splunk Add-on for Salesforce Streaming API.

**Installation:**

- This add-on is intended to be installed on Splunk Search Heads as an extension to either Splunk Add-on for Salesforce or Splunk Add-on for Salesforce Streaming API.

- Log ingestion using the TA Splunk Add-on for Salesforce (https://splunkbase.splunk.com/app/3549)

Alongside Splunk Add-on for Salesforce, overwrite the following:

[sfdc:loginhistory] app and vendor_product
[sfdc:logfile] action, app, object, and vendor_product

Enable saved search "Search - Salesforce User Account Details - Lookup Gen" to enhance user account details (user_id >> user) and "Search - CCX Salesforce User Account Update - Lookup Gen" to support user account details for sfdc:setupaudittrail

- Log ingestion using the TA Splunk Add-on for Salesforce Streaming API (https://splunkbase.splunk.com/app/5689)

Alongside Splunk Add-on for Salesforce Streaming API, overwrite the following fields:

- [sfdc-streaming-api-events:login] action, and status
- [sfdc-streaming-api-events:report] action, app, vendor_product, and src
- [sfdc-streaming-api-events:security] vendor_product

**Known issues:**

- Do not enable the saved search "Lookup - USER_ID to USER_NAME" - this search is not efficient to maintain the user lookup details history.
