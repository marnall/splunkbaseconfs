Cofense Triage Add-On
==========================

# OVERVIEW

The Cofense Triage Add-On is used to query against the Cofense Triage Appliance
to pull back various data.

* Author - Cofense Inc.
* Version - 2.1.7
* Creates Index - False
* Prerequisites - This application requires appropriate credentials to query
  data from Cofense Triage platform. For Details refer to Configuration > Add
  Cofense Triage Account section.
* Compatible with:
    * Splunk Enterprise version: 10.2.x, 10.0.x, 9.3.x, 9.3.x, 9.2.x, 9.1.x, 9.0.x, 8.2.x, 8.1.x, and 8.0.x
    * REST API: v2
    * OS: Platform independent
    * Browser: Safari, Chrome, Firefox, and Microsoft Edge

# RELEASE NOTES VERSION 2.1.7

* Enhanced ingestion logic to prevent duplicate data creation during intermittent connection issues (e.g., network or VPN disruptions).

# RELEASE NOTES VERSION 2.1.6

* Updated AOB version 4.1.5

# RELEASE NOTES VERSION 2.1.5

* Updated splunklib

# RELEASE NOTES VERSION 2.1.4

* Updated AOB version 4.1.4

# RELEASE NOTES VERSION 2.1.2

* Added **props.conf** file.

# RELEASE NOTES VERSION 2.1.1

* Updated the functionality for the endpoint **Reports, Reports - Inbox, Reports- Processed, Reports - Reconnaissance, Cluster, Categories, Attachments**. The endpoint for Reports, will allow administrators to create an input to ingest data based on report location (Inbox, Reconnaissance, and/or Processed). Additionally, each report endpoint input can be configured to ingest report attributes such as URLs, domains, attachments, threat indicators, and data from the report comments file.
* Administrators who currently ingest report data (reports, inbox, processed, reconnaissance) and cluster data, and who wish to edit their input(s) to select “Report Feed Options” (attachments, domains, hostnames, reporter, headers, comments, threat indicators) and “Exclude Options” (raw_headers, html_body, text_body), as well as the cluster input “Cluster Feed Options” (URLs, Hostnames, Domains), will want to note the following:
  * It is recommended if an input is changed by editing, to not reingest historical data as it may create duplicate data entries (the previous data ingested, and then the field changes with the input edit). Instead, an input change should expect data ingestion that is new since the last polling interval. Consider the change to be as of the present and for subsequent polling going forward as opposed to reingesting, as reingestion may create duplicate entries.
* This version of Add-On will effectively support following endpoints for data
  collection (for API v2):
    * Attachment Payloads
    * Attachments
    * Categories
    * Clusters
    * Comments
    * Executive Summary
    * Headers
    * Hostname
    * Integrations
    * Operators
    * Playbooks
    * Reporters
    * Reports
    * Reports - Inbox
    * Reports - Processed
    * Reports - Reconnaissance
    * Rules
    * Status
    * Threat Indicators
    * URLs

# RELEASE NOTES VERSION 2.1.0

* Updated code to match Splunk Add-on Builder 4.0.0.
* Removed support for responses endpoint.
* This version of Add-On will effectively support following endpoints for data
  collection (for API v2):
    * Attachment Payloads
    * Attachments
    * Categories
    * Clusters
    * Comments
    * Executive Summary
    * Headers
    * Hostname
    * Integrations
    * Operators
    * Reporters
    * Reports
    * Reports - Inbox
    * Reports - Processed
    * Reports - Reconnaissance
    * Rules
    * Status
    * Threat Indicators
    * URLs

# RELEASE NOTES VERSION 2.0.1

* Updated the product icons.

# RELEASE HISTORY VERSION 2.0.0

* Added support for API version v2.
* This version of Add-On will support following endpoints for data collection:
    * Attachment Payloads
    * Attachments
    * Categories
    * Clusters
    * Comments
    * Executive Summary
    * Headers
    * Hostname
    * Integrations
    * Operators
    * Reporters
    * Reports
    * Reports - Inbox
    * Reports - Processed
    * Reports - Reconnaissance
    * Responses
    * Rules
    * Status
    * Threat Indicators
    * URLs
* Moved Host URL to the configuration page.
* Reduced inputs from four to one, and added single dropdown for all endpoints.

# RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk configuration which can be found
  here: https://docs.splunk.com/Documentation/Splunk/latest/Capacity/Referencehardware

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app can be set up in two ways:

    1. **Standalone Mode**:
        * Install the Cofense Triage Add-On.
    2. **Distributed Environment**:
        * Install the Cofense Triage Add-On on the search head. User does not
          need to configure an account or create an input in Cofense Triage
          Add-on on search head.
        * Install only Cofense Triage Add-on on the heavy forwarder. User needs
          to configure account and needs to create data input to collect data
          from Cofense Triage platform.
        * User needs to manually create an index on the indexer (No need to
          install Cofense Triage Add-on on indexer).

# INSTALLATION

Cofense Triage Add-On can be installed through UI using "Manage Apps" > "Install
app from file" or by extracting tarball directly into $SPLUNK_HOME/etc/apps/
folder.

# CONFIGURATION

Users will be required to have admin_all_objects capability in order to
configure Cofense Triage Add-On. This Add-on allows a user to configure multiple
account of Cofense Triage Instance. In case a user is using the integration in
search head cluster environment, configuration on all the search cluster nodes
will be overwritten as and when a user changes some configuration on any one of
the search head cluster members. Hence a user should configure the integration
on only one of the search head cluster members. Once the installation is done
successfully, follow the below steps to configure.

## 1. Add Cofense Triage Account

To configure Cofense Triage account, navigate to Cofense Triage Add-On, click
on "Configuration", go to "Accounts" tab, click on "Add" button and fill in the
details asked and click "Add". Field descriptions are as below:

| Field Name                 | Field Description                             |
|----------------------------|-----------------------------------------------|
| Account Name`*`            | Unique name for your account                  |
| Client ID`*`               | Client ID of your Cofense Triage account      |
| Client Secret`*`           | Client Secret corresponding to your Client ID |
| Cofense Triage Host URL`*` | Host URL of your Cofense Triage instance      |

**Note**: `*` denotes required fields

## 2. Configure Proxy (Required only if the requests should go via proxy server)

Navigate to Cofense Triage Add-On, click on "Configuration", go to the "Proxy"
tab, fill in the details asked and click "Save". Field descriptions are as
below:

| Field Name    | Field Description                                                              |
|---------------|--------------------------------------------------------------------------------|
| Enable        | Enable/Disable proxy                                                           |
| Proxy Type`*` | Type of proxy                                                                  |
| Host`*`       | Hostname/IP Address of the proxy                                               |
| Port`*`       | Port of proxy                                                                  |
| Username      | Username for proxy authentication (Username and Password are inclusive fields) |
| Password      | Password for proxy authentication (Username and Password are inclusive fields) |

**Note**: `*` denotes required fields

After enabling proxy, re-visit the "Account" tab, edit/create a new account and
save it to verify if the proxy is working.

## 3. Configure Logging (Optional)

Navigate to Cofense Triage Add-On, click on "Configuration", go to the "Logging"
tab, select the preferred "Log level" value from the dropdown and click "Save".

## 4. Create Data Inputs

This Add-On allows a user to configure multiple inputs to collect data from
Cofense Triage instance. To create an input, navigate to Cofense Triage Add-on,
click on "Inputs" tab, and click on "Create New Input". Fill in the details
asked and click "Add".

Field descriptions are as below:

| Field Name,             | Field Description                                                                   | Default Value | Comments                                                                                                                                                                                                                                                               |
|-------------------------|-------------------------------------------------------------------------------------|---------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Name`*`                 | Unique name of your data input.                                                     | None          | N/A                                                                                                                                                                                                                                                                    |
| Interval`*`             | Time interval of input in seconds. Interval can be in range of 30 to 86400 seconds. | 300           | N/A                                                                                                                                                                                                                                                                    |
| Index`*`                | Splunk index you wants to index your data into.                                     | default       | N/A                                                                                                                                                                                                                                                                    |
| Global Account`*`       | Account to be used for data collection.                                             | None          | N/A                                                                                                                                                                                                                                                                    |
| Endpoint`*`             | Type of data you want to collect.                                                   | Reports       | If no other report inputs are created, such as Inbox, Reconnaissance, or Processed, the reports endpoint will ingest report attributes from all Cofense Triage report locations.                                                                                       |
| Report Feed Options     | List of attributes associated with Reports.                                         | None          | This option is only visible when you select Reports, Reports - Inbox, Reports- Processed, Reports - Reconnaissance as Endpoint value. Report Feed Options allow for report relationship data to be ingested with reports (examples: URLs, Domains, Threat Indicators). |
| Category Feed Options   | List of attributes associated with Categories.                                      | None          | This option only visible when you select Categories as Endpoint value.                                                                                                                                                                                                 |
| Cluster Feed Options    | List of attributes associated with Clusters.                                        | None          | This option only visible when you select Clusters as Endpoint value. URLs, Hostnames, and Domains can be ingested.                                                                                                                                                     |
| Attachment Feed Options | List of attributes associated with Attachments.                                     | None          | This option only visible when you select Attachments as Endpoint value. The attachment_payload is available if selected.                                                                                                                                               |
| Exclude Options         | List of Reports field. Values are **raw_headers, text_body, html_body**             | None          | This option only visible when you select Reports, Reports - Inbox, Reports- Processed, Reports - Reconnaissance and Categories as Endpoint value. Administrators can choose to exclude text_body, html_body, and raw_headers, from ingestion into Splunk.              |
| Start Time              | Start time in UTC timezone for data collection.                                     | T-6 days      | N/A                                                                                                                                                                                                                                                                    |
| End Time                | End time in UTC timezone for data collection.                                       | None          | N/A                                                                                                                                                                                                                                                                    |
| Re Ingest               | Select this option if you want to re-ingest the data.                               | False         | N/A                                                                                                                                                                                                                                                                    |

**Note**: `*` denotes required fields

**Guidelines**:

* Status and Executive Summary is summary kind of data, so Start Time, End Time,
  and Re Ingest fields will be disabled for those endpoint values.
* Once the input will be created, following fields will be disabled on Edit, to
  prevent data duplication or data loss.
    * Endpoint
    * Start Time
    * End Time
* If End Time is provided, Add-On will collect data between Start Time and End
  Time and will stop collecting data after the data in the range is collected.
* If Re Ingest is checked, the Add-On will collect data in the given time
  range (default values will be used in case they are left empty), and then the
  checkbox will be un-checked and regular data collection will continue for that
  input.
* We are not restricting users with limited historical data, but it is
  recommended not to collect data older than 12 months as it might impact Add-On
  performance.

# UPGRADE

## Upgrade from Cofense Triage Add-On v2.1.0 to v2.1.1
* Disable all the existing inputs.
* You can upgrade an App using either the App Management page or the App 
  Browser page in Splunk Web.
  * To update an App using the App Management page:
    * In Splunk Web, click **Apps > Manage Apps**.
    * Find your App, then click Update Available to install the new version.
  * To update an App using the App Browser page:
    * In Splunk Web, click **Apps > Find More Apps**.
    * Find your App, then click Update.
* Restart the Splunk if prompted.

## Upgrade from Cofense Triage Add-On v2.0.x to v2.1.0

* Disable all the existing inputs.
* Install the Cofense Triage Add-On v2.1.0.
* Restart the Splunk if prompted.

## Upgrade from Cofense Triage Add-On v1.x.x to v2.x.x

Upgrade from Cofense Triage Add-On v1.x.x to v2.x.x is NOT supported. Still one
can install v2.x.x of Cofense Triage Add-On by following the steps mentioned
below:

* Disable all the existing inputs.
* Remove all the configured accounts.
* Install the Cofense Triage Add-On v2.x.x.
* Restart the Splunk if prompted.
* Navigate to Cofense Triage Add-On and perform the Configuration as mentioned
  in above section.

# OPEN SOURCE COMPONENTS AND LICENSES

Some of the components included in "Cofense Triage Add-On" are licensed under
free or open source licenses. We wish to thank the contributors to those
projects.

* requests version 2.22.0 https://pypi.org/project/requests (
  LICENSE https://github.com/requests/requests/blob/master/LICENSE)

# TROUBLESHOOTING

* Authentication Failure: Check the network connectivity and verify that the
  configuration details provided are correct.
* Ensure that the KV store is enabled. You can check that by
  visiting: https://localhost:8089/servicesNS/nobody/TA-cofense-triage-add-on-for-splunk/storage/collections/data/TA_cofense_triage_add_on_for_splunk_checkpointer
* For any other unknown failure, please check the
  $SPLUNK_HOME/var/log/ta_cofense_triage_*.log files to get more details on the
  issue. Same logs can be viewed in Search
  using `index=_internal  sourcetype="tacofensetriage:log"`
* App icons are not showing up: The Add-On does not require restart after the
  installation in order for all functionalities to work. However, the icons will
  be visible after one Splunk restart post installation.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex:
/opt/splunk

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/TA-cofense-triage-add-on-for-splunk/
* Remove $SPLUNK_HOME/var/log/ta_cofense_triage_*.log
* To reflect the cleanup changes in UI, restart Splunk instance.
  Refer https://docs.splunk.com/Documentation/Splunk/latest/Admin/StartSplunk
  documentation to get information on how to restart Splunk.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex:
/opt/splunk

# SUPPORT

* Support Offered: Yes
* Support Email: support@cofense.com

# COPYRIGHT

Copyright (c) 2023 Cofense. All rights reserved.

