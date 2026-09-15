[airtable_auditlogs://<name>]

enterprise_account_id = <value>
* Required. The Airtable enterprise account ID, format entXXXXXXXXXXXXXX.
* Obtain from the Airtable admin panel or from your Airtable account team.

token_realm = <value>
* Optional. The realm used to store the Personal Access Token in Splunk's
* credential store (storage/passwords). Defaults to airtable_auditlogs.

token_username = <value>
* Required. The username key under which the Personal Access Token is stored
* in Splunk's credential store. The PAT itself is never placed in this file.

categories = <value>
* Optional. Comma separated list of Airtable audit log categories to collect.
* Leave blank to collect all categories.
* Valid values: base, baseCollaboration, groups, role, share, user,
*   twoFactorAuthentication, oauth, personalAccessToken, enterprise,
*   enterpriseSettings, enterpriseLicenses, managedApps, components,
*   publishedDataSets, dataTable, workspace, workspaceCollaboration,
*   interface, standaloneForms, interfaceCollaboration, view, ai, solution,
*   portal, workflow, customDomain

event_types = <value>
* Optional. Comma separated list of specific audit log event types to collect.
* Maximum 100 values. If set, this takes precedence over categories.

exclude_event_types = <value>
* Optional. Comma separated list of event types to drop before indexing.
* Applied client side, after retrieval. Use this to suppress high volume or
* unwanted events such as loginUser, viewBase and viewShare.

page_size = <value>
* Optional. Events per API page. Maximum 1000. Defaults to 1000.

initial_start_time = <value>
* Optional. ISO 8601 timestamp used only on the very first run, to backfill.
* Example: 2026-07-01T00:00:00Z
* Airtable retains audit log events for 180 days. A value older than that
* is rejected by the API. If blank, collection starts from the retention
* window boundary.

request_timeout = <value>
* Optional. HTTP timeout in seconds for each API call. Defaults to 60.

max_pages_per_run = <value>
* Optional. Safety cap on pages fetched per interval, to bound a backfill.
* Defaults to 100. Set to 0 for unlimited.
