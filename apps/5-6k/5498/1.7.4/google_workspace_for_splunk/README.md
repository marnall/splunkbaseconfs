# Welcome to Google Workspace For Splunk App’s documentation!

## About Google Workspace For Splunk

|                           |                                                |
|---------------------------|------------------------------------------------|
| Author                    | Kyle Smith                                     |
| App Version               | 1.7.4                                          |
| App Build                 | 477                                            |
| Release Date              | 2025-10-07                                     |
| Vendor Products           | Google Workspace, using Service Accounts       |
| Has index-time operations | false                                          |
| Creates an index          | false                                          |
| Implements summarization  | Currently, the app does not generate summaries |

Google Workspace For Splunk allows a Splunk Enterprise administrator to interface with Google Workspace, consuming the usage and administrative logs provided by Google. The limitations on collection times are specified: <https://support.google.com/a/answer/7061566> .

## Scripts and binaries

This App provides the following scripts:

|                                            |                                                                                   |
|--------------------------------------------|-----------------------------------------------------------------------------------|
| ga.py                                      | This python file controls the modular input for Admin Reports                     |
| ga_alerts.py                               | This Python controls the modular input for Alert Center                           |
| ga_usage.py                                | This Python controls the modular input for Admin Usage Reports                    |
| ga_classroom.py                            | This python controls the modular input for Google Classroom Reports               |
| google_client.py                           | This contains the classes for use with the modular inputs                         |
| ga_bigquery.py                             | This contains the classes required for the Big Query inputs.                      |
| ga_ss.py                                   | This contains the classes required for Spreadsheet inputs.                        |
| ga_forms.py                                | This contains the classes required for Google Form inputs.                        |
| ga_analytics.py                            | This contains the items required for Google Analytics Consumption.                |
| Diag.py                                    | Allows diag-targeted collection of information.                                   |
| ModularInput.py                            | Inheritable Class to create Modular Inputs                                        |
| Utilities.py                               | Allows utility interactions with Splunk Endpoints                                 |
| version.py                                 | This is used for localized variables.                                             |
| ga_display_checkpoints.py                  | This is an endpoint to read and display the localized checkpoints.                |
| googleworkspace-write-big-query.py         | This is the alert action file to write to big query.                              |
| googleworkspace-pubsub.py                  | This is the alert action file to read/write from pubsub                           |
| ga_cmd_natural_language.py                 | This is an experimental command to use the Google Natural Language API.           |
| ga_spreadsheets.py                         | This is used to interact with Google Sheets.                                      |
| googleworkspace-vault-hold.py              | This is an experimental alert action to work with the Google Vault.               |
| googleworkspace-vault-matter.py            | This is an experimental alert action to work with the Google Vault.               |
| googleworkspace-alert-action-gmail-send.py | This is an alert action to send emails with different Providers.                  |
| google_constants.py                        | This file holds configurations common to all Google knowledge objects and scripts |
| google_alert_action.py                     | This is the base class for alert actions in this extension                        |
| google_workspace_for_splunk.py             | This is the base script file for the extension.                                   |
| google_utilities.py                        | This holds various utility needs to interface with Splunk.                        |
| cim_actions.py                             | This is related to CIM and Adaptive Response.                                     |
| AlertAction.py                             | This is the base alert action class.                                              |
| \_\_init\_\_.py                            | Module init.                                                                      |
| google_custom_command.py                   | This is the base custom command class.                                            |
| ga_analytics_metadata.py                   | This interacts with the Google Analytics API                                      |
| six.py                                     | Six.                                                                              |
| ga_forms_get.py                            | This interacts with the Google Forms API.                                         |
| app_properties.py                          | This contains several properties for use in python files.                         |
| KennyLoggins.py                            | An updated and enhanced logging class.                                            |
| \_paths.py                                 | Global import to target `lib` folder.                                             |

## About this release

Version 1.7.4 of Google Workspace For Splunk is compatible with:

|                            |                                             |
|----------------------------|---------------------------------------------|
| Splunk Enterprise versions | 10.0, 9.4                                   |
| Platforms                  | Splunk Enterprise, Splunk Cloud (if vetted) |

Compatability

## Known Issues

Version 1.7.4 of Google Workspace For Splunk has the following known issues:

- According to stackoverflow, there are indications that the Google Apps Admin API has an unspecified delay introduced into the events that are collected. This is most likely due to how Google collects the events and the global nature of the events. To mitigate this issue, the Google Workspace For Splunk Modular Input has a built-in delay in the consumption of events. If you run the modular input at 30 minutes, there will be a 30 minute delay of events. If you run at 1 hour, there will be a 1 hour delay in events.

- References

  - <https://support.google.com/a/answer/7061566>

  - <http://stackoverflow.com/questions/27389354/minimal-delay-when-listing-activities-using-the-reports-api>

  - <http://stackoverflow.com/questions/30850838/what-is-the-delay-between-a-event-happens-and-it-is-reflected-in-admin-reports-a>

- These are the currently used scopes. Not all scopes are required to be used.

  - <https://www.googleapis.com/auth/admin.reports.audit.readonly>

  - <https://www.googleapis.com/auth/admin.reports.usage.readonly>

  - <https://www.googleapis.com/auth/admin.directory.user.readonly>

  - <https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly>

  - <https://www.googleapis.com/auth/drive.metadata.readonly>

  - <https://www.googleapis.com/auth/bigquery>

  - <https://www.googleapis.com/auth/cloud-platform>

  - <https://www.googleapis.com/auth/drive.readonly>

  - <https://www.googleapis.com/auth/spreadsheets>

  - <https://www.googleapis.com/auth/classroom.courses.readonly>

  - <https://www.googleapis.com/auth/classroom.rosters.readonly>

  - <https://www.googleapis.com/auth/classroom.coursework.students.readonly>

  - <https://www.googleapis.com/auth/classroom.announcements.readonly>

  - <https://www.googleapis.com/auth/classroom.guardianlinks.students.readonly>

  - <https://www.googleapis.com/auth/apps.alerts>

  - <https://www.googleapis.com/auth/gmail.send>

# User Guide

## Key concepts for Google Workspace For Splunk

- You must have enabled the Google Workspace APIs at <https://console.developers.google.com>

- You must have configured a credential for use with this App at <https://console.developers.google.com>.

- You must enable Domain Wide Delegation for the credential.

- You must have a G Suite User with permissions to the correct API scopes. This user will be impersonated.

- Scopes Defined are here: <https://developers.google.com/identity/protocols/googlescopes>

## Create Service Account.

1.  Navigate to <https://console.cloud.google.com/iam-admin/serviceaccounts>

2.  Create/Select a Project

3.  Click Create service account button.

4.  Fill out the information required, and finish creation of the Service Account.

5.  Once created, edit the Service Account.

6.  **Note:** Google Analytics consumption is non-standard from this point. Please see documentation further down for specifics.

7.  Find the Show domain-wide delegation section, and show the section.

8.  Click the check box to enable G Suite Domain-wide Delegation.

9.  If you did not previously have a key created, find the Keys tab and create a new JSON private key for the Service Account

10. SAVE THIS FILE FOR THE NEXT STEPS

11. MAKE NOTE OF THE CLIENT ID OF THIS CREDENTIAL

12. Enable the following APIS while in the console. (As Needed)

    1.  Admin SDK API

    2.  Audit API

    3.  Google Classroom API

    4.  Google Workspace Alert Center API

    5.  Google Sheets API

    6.  BigQuery API

    7.  Cloud Pub/Sub API

    8.  Google Forms API

    9.  Analytics Reporting API

    10. Google Analytics Data API

    11. Google Analytics API

    12. Google Analytics Admin API

    13. Gmail API

## Configure Google Workspaces

1.  Navigate to <https://admin.google.com/ac/users>

2.  Create a new user that has permissions to access the above enabled APIS (some sort of Admin level)

3.  MAKE A NOTE OF THIS USER FOR A LATER STEP

4.  Navigate to <https://admin.google.com/ac/owl/domainwidedelegation>

5.  Click the Add New button

6.  Enter the client id from above, and any scopes you require.

    1.  <https://www.googleapis.com/auth/admin.reports.audit.readonly>

    2.  <https://www.googleapis.com/auth/admin.reports.usage.readonly>

    3.  <https://www.googleapis.com/auth/admin.directory.user.readonly>

    4.  <https://www.googleapis.com/auth/admin.directory.device.chromeos.readonly>

    5.  <https://www.googleapis.com/auth/classroom.courses.readonly>

    6.  <https://www.googleapis.com/auth/classroom.rosters.readonly>

    7.  <https://www.googleapis.com/auth/classroom.coursework.students.readonly>

    8.  <https://www.googleapis.com/auth/classroom.announcements.readonly>

    9.  <https://www.googleapis.com/auth/classroom.guardianlinks.students.readonly>

    10. <https://www.googleapis.com/auth/apps.alerts>

    11. <https://www.googleapis.com/auth/pubsub>

    12. <https://www.googleapis.com/auth/bigquery>

    13. <https://www.googleapis.com/auth/spreadsheets>

    14. <https://www.googleapis.com/auth/drive.readonly>

    15. <https://www.googleapis.com/auth/ediscovery>

    16. <https://www.googleapis.com/auth/analytics.readonly>

    17. <https://www.googleapis.com/auth/gmail.settings.basic>

## Configure Google Workspace Credentials.

1.  Navigate to the Application Configuration dashboard.

2.  Navigate to the Google Workspace Credentials tab.

3.  Download/have on hand the JSON file from the Developers Console for the Service Account Credentials.

4.  Click the + sign at the top right of the table.

5.  Fill out the form, upload the JSON file, and click the checkmark to the left of the row.

6.  The Entire contents of the JSON file will be stored in the encrypted credential store.

## Configure the Admin Reports Inputs

Requires  
Audit API

Each API endpoint has individual APIs that need to be enabled within <https://console.developers.google.com>.

1.  For each Report that would like to be consumed, configure a new row for that report. One report per credential per row.

    1.  Lookback - this setting will consume that many days back from the API. This is a first-run-to-completion flag only.

    2.  Interval - Each report has a slightly different recommended interval.

        1.  Please review <https://support.google.com/a/answer/7061566> and schedule the input service interval accordingly.

## Configure the Admin Usage Inputs

Requires  
- Admin SDK API

- GMail API (for Directory based Email Forwarding Settings Consumption)

Each API endpoint has individual APIs that need to be enabled within <https://console.developers.google.com>.

1.  For each Report that would like to be consumed, configure a new row for that report. One report per credential per row.

    1.  Lookback - this setting will consume that many days back from the API. This is a first-run-to-completion flag only.

    2.  Interval - Each report has a slightly different recommended interval.

        1.  Please review <https://support.google.com/a/answer/7061566> and schedule the input service interval accordingly.

2.  Usage - User, Customer, Directory

    1.  These should be scheduled for cron expressions to prevent massive data ingest. Typically 1 (once) per day per input.

3.  Directory

    1.  If the status of email forwarding would like to be consumed, click the corresponding checkbox.

    2.  The forwarding address settings will be found in mail.settings.forwardingAddresses item of the directory user event.

## Configure the Alert Center Inputs

Requires  
Google Workspace Alert Center API

For each alert center, configure a row in the table to pull the information desired. View more information at <https://developers.google.com/admin-sdk/alertcenter/reference/alert-types> .

## Configure the Email Alert Action

Requires  
Google Workspace Gmail API

More information is located at: <https://developers.google.com/workspace/gmail/api/guides> . In order to use this API, an "Impersonation User" must be defined in the Credential Management.

Additionally, the SMTP Alert Action can be used with a local SMTP connection string. The format is `smtp[s]://[username:password@]server:port`. Splunk Cloud uses the connection string: `smtp://localhost:25`. The actual settings can be found in your Splunk Cloud instance under the uri `/manager/search/admin/alert_actions/email?action=edit`.

### Jinja2 Compatibility

Both the `message` and the `subject` support templating using Jinja2 (<https://pypi.org/project/Jinja2/>). The variables passed are the following object:

\`\`\` { "savedsearch": string, "results_file": string, "event_fields": \[\]string, "evts": \[\]object, "single_email": boolean, } \`\`\`

To reference a field in the template, use the following notation:

`{{evts[0].sourcetype}}`

This example will use the first item in the array and use its sourcetype field name. Looping is supported via Jinja2 looping formats. If `single_email` is `true`, then `evts` will contain ALL the events from the search, otherwise only a single row will be provided.

The templates can be defined either in the Alert Action, or via field in result. Fields supported within the results:

- `body_template`

- `recipients`

- `cc`

- `bcc`

- `subject`

- `sender`

If one of those fields is detected, the value in the field will over-write the one provided in the alert action. This allows for a lookup file to be used for specific use cases, if applicable.

## Configure Classroom Inputs

Requires  
Google Classroom API

1.  NOTE: Checking the Write Courses Data checkbox for ANY input will cause the input to write out ALL course metadata each pull. To keep the data down to a reasonable level, only configure 1 input to consume that data.

2.  CourseIDs are a comma separated list of specific course ids. If empty, all will be consumed.

3.  Most, if not all, of these could be fine at a 86400 interval.

## Configure Big Query Inputs

Requires  
BigQuery API

1.  For GMail Headers: Documentation From Google

2.  Fill out the fields for the project, dataset, table. If all tables are required from a single dataset, enter an asterisk. \*

3.  The Ingest Type is one of Row, Query, Time.

    1.  Row: is a full pull of the rows from the table. Be careful using on dynamic tables, if any rows are deleted, this will not work as expected.

    2.  Query: Place your SQL query in the Enrichment Field column. You can support checkpointing by using TIMESTAMP in the Query String. The timestamp is a 10 digit integer and is based on the last execution time of the input. THIS MAY INCUR COSTS.

    3.  Time: This is a very simple query. Uses a checkpoint time, and the “Time field” that is in the Enrichment Field ( iso_time for example). It will consume all fields and columns from the data. THIS MAY INCUR COSTS.

    4.  Virtual Row: is a pull of all the rows of VIEW, but checkpointed per vuew. This allows for a virtual table to be pulled while respecting the row counts of the larger table. This should be used with GMail Audit Logs. Dataset and Project required, any VIEWS will be queried and checkpointed. THIS MAY INCUR COSTS.

4.  The Starting Index is a “first time only” setting. Consumption will start from that row line, and will be checkpointed after first run. This can also be a timestamp for Ingest Types of Time and Query (10 digit)

5.  Highly environmentally dependent for speed of consumption. Work with max_rows setting to determine proper messages per interval. Default is 250,000.

<div class="note">

Query, Virtual Row, and Time ingest types are EXPENSIVE. I AM NOT LIABLE FOR YOUR SPENDING. Queries (on-demand) \$5 per TB The first 1 TB per month is free.

</div>

## Configure PubSub Inputs

Requires:

- Cloud Pub/Sub API

Fill out the row with appropriate settings. Work with Max Messages to determine proper messages per interval setting for the environment.

<div class="note">

Pubsub requires the use of grpcio binaries. Only a “many linux x64” file is included with this app. Please follow these instructions if you see any errors with the search:

</div>

    index=_internal log_level=ERROR sourcetype=``google:workspaces:modularinput:pubsub''error_filename=``ga_pubsub.py'' | stats values(error_*) as error_* by input_guid input_name

1.  Consult The Project Page and download the file that matches Python 3.7 and your filesystem. Download it to \$SPLUNK_HOME/etc/apps/google_workspace_for_splunk/lib

2.  Cd to that same folder, and execute unzip -n \<package\>.whl, or an equivalent command on the OS required.

3.  This will install the .so file to the location required for the Scripts to work.

## Configure Spreadsheet Inputs

Requires  
- Google Drive API

- Google Sheets API

  1.  Select the credential that you want to use.

  2.  Select the “Spreadsheet” dropdown. This should auto-populate with the spreadsheets that are allowed for the impersonation user configured on the credential.

  3.  Select the Sheets (multiple allowed) to consume.

  4.  Set the destination

      1.  KVStore

          1.  Takes the sheets, and places the data into KVStore lookups.

          2.  Ordered: Keeps row and column placements for a true “re-structure” of the data.

          3.  UnOrdered: consumes each column as a “key value” into the lookup.

      2.  CSV

          1.  Takes the sheets, and places the data into CSV lookups.

          2.  Ordered: Keeps row and column placements for a true “re-structure” of the data.

          3.  UnOrdered: consumes each column as a “key value” into the lookup.

      3.  Indexed

          1.  Takes the contents of the sheets, and places the data into an index.

## Configure Vault Inputs

TBD - maybe.

## Configure Forms Inputs

Requires  
Google Forms API

Scopes  
- <https://www.googleapis.com/auth/forms.body.readonly>

- <https://www.googleapis.com/auth/forms.responses.readonly>

- <https://www.googleapis.com/auth/drive.readonly>

  1.  Select the credential that you want to use.

  2.  Select the “Form” dropdown. This should auto-populate with the forms that are allowed for the impersonation user configured on the credential.

  3.  Set the destination

      1.  KVStore

          1.  Takes the form data, and places the data into KVStore lookups.

          2.  Ordered: Keeps row and column placements for a true “re-structure” of the data.

          3.  UnOrdered: consumes each column as a “key value” into the lookup.

      2.  CSV

          1.  Takes the form data, and places the data into CSV lookups.

          2.  Ordered: Keeps row and column placements for a true “re-structure” of the data.

          3.  UnOrdered: consumes each column as a “key value” into the lookup.

      3.  Indexed

          1.  Takes the contents of the form data, and places the data into an index.

## Configure Analytics Inputs

Requires  
- Google Analytics Data API (v4 properties)

- Google Analytics Admin API (v4 properties)

NOTE  
THIS INPUT IS Google Analytics v4 only. Earlier versions will not work.

Scopes  
- <https://www.googleapis.com/auth/analytics.readonly>

<div class="note">

This input uses “NON DELEGATED” credentials. Meaning, Google Workspace USERS will NOT WORK with the Google Analytics Properties. In order to use this input, make sure to collect the email address of the credential (should be something like \<credential_name\>@\<gcp_project\>.iam.gserviceaccount.com ). This email should be granted permissions (Viewer will work) on EACH of the Google Analytics Properties that it is required to access. There is no Google Workspace Domain Delegation for this input.

</div>

<div class="note">

FOR GA4 Properties, this will need to be consulted. <https://ga-dev-tools.web.app/ga4/dimensions-metrics-explorer/> . The metrics/dimensions of GA4 properties are more cumbersome than in previous versions.

</div>

1.  Enter a distinguishing name

2.  Select a credential from the dropdown

    1.  The fields View, Metrics, Dimensions should autopopulate based on the Google Analytics Metadata API.

3.  Select a View from the dropdown.

    1.  These are all the properties the credential is allowed to access.

    2.  Maximum 1 can be chosen per input.

4.  Select some Metrics to query from the API.

    1.  Maximum of 10 can be chosen at once.

5.  Select some Dimensions to query from the API.

    1.  Maximum of 9 can be chosen at once.

6.  **NOTE:** Prior to saving the input, click the “Check Compatability” link. Any incompatibility between metrics and dimensions will be alerted upon.

7.  **NOTE:** There are 3 dimensions that deal with timestamps. `date`, `dateHour` and `dateHourMinute`. The recommendation is to use the ga:dateHourMinute dimension for v3 properties, and ga:dateHour for v4 properties.

8.  Select a Time Field, if required.

    1.  If selected, it should also be present in the Dimensions field.

    2.  If not selected, the data of metrics and dimensions will be set with the timestamp of the modular input execution.

9.  Enter a Backfill, if history is required.

    1.  This is performed on *every* interval, however, if the date is already present in the checkpoint file, it will ignore it.

    2.  Additionally, to prevent checkpoint bloat, there is a hard coded “7 + backfill” limit on the number of days that the checkpoint will keep track of.

    3.  In theory, this will allow a system down for 7 days , with a backfill of greater than 7, to pull additional data during the outage.

    4.  Backfill is recommended to be set at 14 for normal operations. Higher values can be used, and then once data is consumed and verified, the backfill can be lowered.

10. If needed, select an index to populate.

    1.  An index can be defined manually by typing in the box.

11. Enter a cron interval.

    1.  Data returned will be “yesterdays” data.

    2.  This is a Splunk-valid cron expression. See here for more information.

    3.  A cron is required, seconds are not permitted as an interval.

    4.  This is recommended to be executed near the end of the day. 2330 (11:30 PM) is recommended due to allow data to become “golden”.

12. **NOTE:** REALTIME Google Analytics Data is not currently supported.

## Indexes

By default, all events will be written to the “main” index. You should change the index in the configuration files to match your specific index.

## Configure Proxy Support

This App Supports proxy configuration. Configure the proxy first in the Application Configuration dashboard, and then choose it during the Google workspace Credential configuration.

## Troubleshoot Google Workspace For Splunk

1.  Check the Monitoring Console (\>=v6.5) for errors

2.  Visit the Application Health dashboard

## CIM

As of v1.5.0 of this app, CIM is not guaranteed, but should be available.

## EXPERIMENTAL

There are portions of this app that are experimental, or you might see “odd” code. This is for some up coming features, might work, might not.

- Custom Commands - EXPERIMENTAL

  - `gwlanguage`: Currently a work in progress.

## Lookups

Google Workspace For Splunk contains the following lookup files:

- None

## Event Generator

Google Workspace For Splunk does not make use of an event generator.

## Acceleration

1.  Summary Indexing: No

2.  Data Model Acceleration: No

3.  Report Acceleration: No

## Binary File Declaration

1.  lib/google/protobuf/internal/\_api_implementation.cpython-38-darwin.so is apparently a binary file. Required for Google Things.

2.  lib/google/protobuf/pyext/\_message.cpython-38-darwin.so is apparently a binary file. Required for Google Things.

3.  lib/grpc/\_cython/cygrpc.cpython-37m-x86_64-linux-gnu.so is a binary file. Required for Google PubSub Things on Linux. For these two, please see <https://github.com/protocolbuffers/protobuf/tree/3.6.x/python/google/protobuf/internal> for source and attribution.

4.  `recarray_from_file` is a binary file. Required for numpy third-party library. (lib/numpy/core/tests/data/recarray_from_file.fits)

5.  `libnpymath` is a binary file. Required for numpy third-party library. (lib/numpy/core/lib/libnpymath.a)

6.  `libnpyrandom` is a binary file. Required for numpy third-party library. (lib/numpy/random/lib/libnpyrandom.a)

7.  `plasma-store-server` is a binary file. Required for pyarrow package. (lib/pyarrow/plasma-store-server)

<!-- -->

    _cffi_backend: Required for third-party library.
    md: Required for third-party library.
    native: Required for third-party library.
    _umath_tests: Required for third-party library.
    _multiarray_umath: Required for third-party library.
    _rational_tests: Required for third-party library.
    _multiarray_tests: Required for third-party library.
    _simd: Required for third-party library.
    _struct_ufunc_tests: Required for third-party library.
    _operand_flag_tests: Required for third-party library.
    _pocketfft_internal: Required for third-party library.
    _umath_linalg: Required for third-party library.
    lapack_lite: Required for third-party library.
    _bounded_integers: Required for third-party library.
    _common: Required for third-party library.
    _generator: Required for third-party library.
    _mt19937: Required for third-party library.
    _pcg64: Required for third-party library.
    _philox: Required for third-party library.
    _sfc64: Required for third-party library.
    bit_generator: Required for third-party library.
    mtrand: Required for third-party library.
    libgfortran-2e0d59d6: Required for third-party library.
    md__mypyc: Required for third-party library
    libopenblasp-r0-2d23e62b: Required for third-party library
    libquadmath-2d0c479f: Required for third-party library
    _crc32c: Required for third-party library
    libcrc32c-7ebc40c5: Required for third-party library
    _yaml: Required for third-party library

# Installation and Configuration

## Software requirements

### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## Download

Download Google Workspace For Splunk at <https://splunkbase.splunk.com/app/5498>.

## Installation steps

### Deploy to single server instance

1\. Deploy as you would any App, and restart Splunk. 1. NOTE: Only the App is required. Install only 1 of the Google Workspace add ons or app. 1. Configure.

### Deploy to Splunk Cloud

1\. Have your Splunk Cloud Support handle this installation. 1. You may consider using an on-premise Heavy Forwarder to install Google Workspace For Splunk, and send the logs to Splunk Cloud.

### Deploy to a Distributed Environment

1\. For each Search Head in the environment, deploy a non-configured copy of the App. 1. For each indexer in the environment, deploy a copy of the Google Workspace For Splunk App that is located as mentioned above. 1. For a single “Data Collection Node” OR “Heavy Forwarder” OR “IDM (splunk Cloud)” (a full instance of Splunk is required), install Google Workspace For Splunk and configure through the GUI. :package: google_workspace_for_splunk :description: The Google Workspace For Splunk App will connect to your Google Workspace instance and pull configured data for the domain :long_name: Google Workspace For Splunk :version: 1.7.4 :app_author: alacercogitatus :build: 477 :splunk_versions: 10.0, 9.4 :splunkbase_url: <https://splunkbase.splunk.com/app/5498> :base_color: \#757575 :menu_slide_auto_close: false :include_app_setup: true :alert_actions: googleworkspace-pubsub,googleworkspace-vault-matter,googleworkspace-vault-hold :modularinput_name: ga :force_configuration: false :configuration_view: App_Config == Support and resources

## Questions and answers

Access questions and answers specific to Google Workspace For Splunk at <https://answers.splunk.com> . Be sure to tag your question with the App.

## Support

- Support Email: splunkapps @kyleasmith .info

- Support Offered: Community Engagement

Support is available via email at

splunkapps

@kyleasmith

<div class="formalpara-title">

**info.**

</div>

You can also find the author on Splunk Usergroups Slack. Feel free to email or ping, most responses will be within 1-2 business days, but not guarenteed. This is not a service SLA commitment, I am not obligated to answer anything. But I generally do.

### Diagnostics Generation

If a support representative asks for it, a support diagnostic file can be generated. Use the following command to generate the file. Send the resulting file to support.

    $SPLUNK_HOME/bin/splunk diag –collect=app:google_workspace_for_splunk

# Release notes

## Version 1.7.4

- NEW ALERT ACTION SEND EMAIL

  - A new alert action "Google Send Email" can be used to send an email using a Google Service Account (with impersonation user), a local SMTP Server, OR Splunk Cloud SMTP!

  - Splunk Cloud SMTP connection string should be \`\`

  - TEMPLATES!

    - This alert action can use Jinja2 Compatible templates from either the alert action or inline SPL.

- Verification for Splunk Enterprise 10.0.0 and Splunk Cloud (10.0.2503.6)

## Version 1.7.3

- **BREAKING CHANGE**

  - Updated scopes for directory (email forwarding) ingest from `https://www.googleapis.com/auth/gmail.settings.basic` to `https://www.googleapis.com/auth/gmail.readonly`

  - The new scope will need to be added to the domain delegation for the service credential.

- Improvement

  - Updated Admin ingest configuration tab to allow multiple selects per input to reduce input count.

## Version 1.7.2

- Improvement

  - Consolidated Metadata endpoints to reduce possible exposures

  - Updated `PubSub` and `BigQuery` Input UI to auto-detect and present relevant and accessible field values for `project`, etc.

- Bug

  - Removed references to `app_dirs` that was causing bad imports in certain Splunk Cloud configurations.

- Tested Versions

  - Splunk Enterprise `9.3.4` and `9.4.2`

  - Splunk Cloud `9.3.2411.108`

## Version 1.7.1

- Bug

  - Fixed chmod on .so files

## Version 1.7.0

- New Features

  - \[GSUITE-70\] New Input type to consume **only** a specific user.

- Improvements

  - Updated to ensure compliance with OpenSSL and Node upgrades in core Splunk.

  - UI Improvements for configuration.

  - Upgraded various Python Libraries for Python 3.9

- Bug Fixes

  - Alert Center Modular Input did not read the correct checkpoint, resulting in duplicate data ingestion.

  - Updated create triggers in configuration ui to set the toggles correctly on creation.

  - Fixed PubSub max_messages error with null and undefined.

  - Fixed error on Analytics Tab that wouldn’t display available Views.

### Removal of binary files.

These binary files were removed to bypass the incorrect AppInspect check for aarch64 compatible binaries.

- `lib/numpy.libs/libgfortran-2e0d59d6.so.5.0.0`

- `lib/google/_upb/_message.abi3.so`

- `lib/numpy.libs/libquadmath-2d0c479f.so.0.0.0`

- `lib/numpy.libs/libopenblasp-r0-2d23e62b.3.17.so` :package: google_workspace_for_splunk :description: The Google Workspace For Splunk App will connect to your Google Workspace instance and pull configured data for the domain :long_name: Google Workspace For Splunk :version: 1.7.4 :app_author: alacercogitatus :build: 477 :splunk_versions: 10.0, 9.4 :splunkbase_url: <https://splunkbase.splunk.com/app/5498> :base_color: \#757575 :menu_slide_auto_close: false :include_app_setup: true :alert_actions: googleworkspace-pubsub,googleworkspace-vault-matter,googleworkspace-vault-hold :modularinput_name: ga :force_configuration: false :configuration_view: App_Config

# Third Party Notices

Version 1.7.4 of Google Workspace For Splunk incorporates the following Third-party software or third-party services.

## Google Apps APIs

Please visit <https://developers.google.com/google-apps/> for full terms and conditions.

## Aplura, LLC Components

Components Written by Aplura, LLC Copyright © 2016-2017 Aplura, ,LLC

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, eMA 02110-1301, USA.

## defusedxml

## defusedxml

PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2

1\. This LICENSE AGREEMENT is between the Python Software Foundation (“PSF”), and the Individual or Organization (“Licensee”) accessing and otherwise using this software (“Python”) in source or binary form and its associated documentation.

2\. Subject to the terms and conditions of this License Agreement, PSF hereby grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce, analyze, test, perform and/or display publicly, prepare derivative works, distribute, and otherwise use Python alone or in any derivative version, provided, however, that PSF’s License Agreement and PSF’s notice of copyright, i.e., “Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008 Python Software Foundation; All Rights Reserved” are retained in Python alone or in any derivative version prepared by Licensee.

3\. In the event Licensee prepares a derivative work that is based on or incorporates Python or any part thereof, and wants to make the derivative work available to others as provided herein, then Licensee hereby agrees to include in any such work a brief summary of the changes made to Python.

4\. PSF is making Python available to Licensee on an “AS IS” basis. PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED. BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.

5\. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON, OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.

6\. This License Agreement will automatically terminate upon a material breach of its terms and conditions.

7\. Nothing in this License Agreement shall be deemed to create any relationship of agency, partnership, or joint venture between PSF and Licensee. This License Agreement does not grant permission to use PSF trademarks or trade name in a trademark sense to endorse or promote products or services of Licensee, or any third party.

8\. By copying, installing or otherwise using Python, Licensee agrees to be bound by the terms and conditions of this License Agreement.

## markdown.js

Released under the MIT license.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
