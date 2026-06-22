# Microsoft Graph Email Alert Action for Splunk

## Overview

Microsoft Graph Email Alert Action for Splunk provides a custom alert action that sends Splunk alert emails through the Microsoft Graph API.

The app uses Microsoft Entra ID app-only authentication with the OAuth 2.0 client credentials flow. Credentials are stored in Splunk password storage and are used by the alert action at runtime to request a Microsoft Graph access token and send email using the Microsoft Graph sendMail endpoint.

## Features

- Send Splunk alert emails through Microsoft Graph.
- Supports To and CC recipients.
- Supports text or HTML message bodies.
- Supports Splunk alert tokens such as `$name$`, `$results_link$`, and result fields.
- Stores Microsoft Graph credentials in Splunk password storage.
- Designed to run on Splunk search heads.

## Requirements

- Splunk Enterprise or Splunk Cloud Platform.
- Python 3 runtime provided by Splunk.
- Network access from the Splunk search head to `https://login.microsoftonline.com`.
- Network access from the Splunk search head to `https://graph.microsoft.com`.
- Microsoft Entra ID app registration with Microsoft Graph API permissions.

## Microsoft Entra ID Setup

Create an app registration in Microsoft Entra ID.

Record the following values:

- Tenant ID
- Client ID
- Client Secret
- Sender mailbox address

Add the following Microsoft Graph API permission:

- Microsoft Graph
- Application permission
- Mail.Send

Grant admin consent for the permission.

The sender mailbox must exist in Microsoft 365 and must be allowed to send mail through Microsoft Graph.

For least privilege, restrict which mailboxes the app registration can access using Microsoft-supported mailbox access controls such as Exchange Application RBAC or application access policies, depending on your Microsoft 365 environment.

## Installation

Install the app on the Splunk search head.

For distributed deployments, install this app on the search head or search head cluster where scheduled alerts run.

The app should not be installed on indexers or forwarders.

## Splunk Configuration

After installation, open the app setup page and enter:

- Tenant ID
- Client ID
- Client Secret
- Sender Email

The app stores this configuration in Splunk password storage.

The credential is stored using:

- Realm: `msgraph`
- Username: `msgraph_credentials`

## Alert Action Configuration

Create or edit a Splunk alert.

Under Trigger Actions, select `Send email via Microsoft Graph`.

Configure the fields below.

### To

Required. Comma-separated list of recipient email addresses.

Example:

`soc@example.com,oncall@example.com`

### CC

Optional. Comma-separated list of CC recipient email addresses.

Example:

`manager@example.com`

### Subject

Required. Supports Splunk alert tokens.

Example:

`Splunk Alert: $name$`

### Message

Required. Supports Splunk alert tokens and result fields.

Example:

`The alert condition for '$name$' was triggered. Results: $results_link$`

## Supported Tokens

The alert action supports standard Splunk alert payload values and first-result fields.

Examples:

- `$name$`
- `$results_link$`
- `$search_name$`
- `$result.host$`
- `$result.source$`
- `$result.sourcetype$`

Available tokens depend on the alert type and the fields returned by the search.

## Roles and Permissions

Users who create scheduled alerts need permission to schedule searches.

Recommended capability:

`schedule_search`

The alert action reads Microsoft Graph credentials from Splunk password storage at runtime. The saved alert owner, or the service account that owns the alert, must be able to read the stored credential.

Required capability:

`list_storage_passwords`

Do not grant `list_storage_passwords` broadly to all users. For production, use a dedicated service account to own and run Microsoft Graph email alerts.

Users who configure the setup page need permission to create or update stored credentials.

Required capability:

`edit_storage_passwords`

## Logs

The app writes its own log file here:

`$SPLUNK_HOME/var/log/splunk/msgraph_send_email.log`

Splunk alert action execution messages can also be found in:

`$SPLUNK_HOME/var/log/splunk/splunkd.log`

Useful search:

`index=_internal (source=*msgraph_send_email.log OR source=*splunkd.log) msgraph_send_email`

## Troubleshooting

### Missing authentication configuration

This means one or more stored credential values are missing:

- `tenant_id`
- `client_id`
- `client_secret`
- `sender_user`

Open the setup page and save the configuration again. Make sure the Client Secret field is populated.

### HTTP 403 from /admin/passwords

Example:

`Client is not authorized to perform requested action /servicesNS/nobody/TA_msgraph_alert/admin/passwords`

The alert owner does not have permission to read Splunk password storage.

Use a service account with `list_storage_passwords`, or adjust role permissions carefully.

### Graph sendMail failed

Confirm:

- The app registration has Microsoft Graph `Mail.Send` Application permission.
- Admin consent has been granted.
- The sender mailbox exists.
- The sender address in setup is correct.
- The Splunk search head can reach Microsoft Graph over HTTPS.

### Alert action "list" not found

This is unrelated to the Microsoft Graph alert action. It means the saved alert contains an invalid alert action named `list`.

Check the saved alert configuration and remove `list` from the configured actions.

## Security Notes

- Client secrets are stored in Splunk password storage.
- Secrets must not be stored in plaintext configuration files.
- Secrets are not written to app logs.
- Outbound communication uses HTTPS.
- The Microsoft Graph app registration should be scoped as narrowly as possible.
- Use a dedicated Splunk service account to own scheduled alerts that use this action.

## Deployment Notes

This app is intended for search heads.

Recommended `app.manifest` target workload:

`"targetWorkloads": ["_search_heads"]`

Recommended supported deployments:

`"supportedDeployments": ["_standalone", "_distributed", "_search_head_clustering"]`

## Compatibility

Tested with:

- Splunk Enterprise 9.x
- Microsoft Graph API v1.0
- Splunk-provided Python 3 runtime

## Support

For support, contact GKC.

## Release Notes

### Version 1.0.0

Initial release.

- Added Microsoft Graph email custom alert action.
- Added setup page for Microsoft Graph credentials.
- Added support for To, CC, Subject, and Message fields.
- Added Splunk alert token rendering.
- Added credential storage using Splunk password storage.
