# Slack Audit App for Splunk

> The Slack Audit App for Splunk gives you critical insights into your Slack Enterprise Grid account.

The app includes:
* A pre-built knowledge base of dashboards that deliver real-time visibility into your environment.
* The dashboards showcase 
    - User Logins and Admin actions such as Users Added
    - Popular App Installations, Approved and Retricted App Details
    - File Activity
    - Workspace Preference Change Activity
    - Private/Public Channel Creations, User/Guest Joins and External Shared Channel Details

## Setup Instructions

The Slack Audit App for Splunk needs Audit log data to be indexed into the **slack_audit** index. 
* Use the Technology Add-on to retrieve Slack Audit Logs : [Slack Add-on for Splunk](https://splunkbase.splunk.com/app/4986/)
* Be sure to set the index to retrieve these logs into, to be named **slack_audit**

### Preferences Activity Dashboard
The Preferences Activity Dashboard has the Event Timeline panel that relies on the [Event Timeline App](https://splunkbase.splunk.com/app/4370/) to be installed. Download the app to see the panel show up.

## Troubleshooting
* Verify that the the Slack Audit Logs are being populated into the right index, i.e., **slack_audit**
* Verify that the Splunk account has access to the index containing the audit logs.
* If not, perform the below steps to change the macro definition :
    - Navigate to *Settings* -> *Advanced Search* -> *Search Macros*
    - Set the App Context to be **Slack Audit App for Splunk**, Owner to be **Any** and **Visible in the App**
    - Click on the macro named **slack_audit_log_index**
    - Under its definition, change the name of the index to the index where slack audit log data is currently being populated. 
    - Should you configure to index audit logs into multiple indexes, for example sending audit logs of different Enterprise Grid Slack Accounts/Organizations into different indexes, change the macro to reflect those indexes as well. For instance :
        * Production Enterprise Slack Account Audit log index : slack_audit
        * Dev Enterprise Slack Account Audit log index : slack_audit_dev
        * New macro definition : (index=slack_audit OR index=slack_audit_dev)
    - Click on *Save* to save the new configuration
    - Re-open the **Slack Audit App for Splunk** to see the dashboards displaying data.
* Preferences Activity dashboard would require installation of the [Event Timeline App](https://splunkbase.splunk.com/app/4370/) 
