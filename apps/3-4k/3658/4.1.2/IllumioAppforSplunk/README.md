# Illumio App for Splunk

* [Overview](#overview)
* [Prerequisites](#prerequisites)
    * [Splunk Architecture](#splunk-architecture)
* [Installation](#installation)
    * [Configuration](#configuration)
* [Upgrade Steps](#upgrade-steps)
* [Custom Roles](#custom-roles)
* [Alerts](#alerts)
* [Saved Searches](#saved-searches)
* [Data Model](#data-model)
    * [Data Model Acceleration](#data-model-acceleration)
* [Known Issues](#known-issues)
* [Troubleshooting](#troubleshooting)
* [Uninstalling](#uninstalling)
* [Release Notes](#release-notes)
* [EULA](#eula)
* [Support](#support)
* [License](#license)

## Overview

The Illumio App for Splunk integrates with the Illumio Policy Compute Engine (PCE) to provide security and operational insights into your Illumio secured data center. A dashboard view displays an overview of the security posture of the data center.  

With improved visibility of east-west traffic, Security Operations Center (SOC) staff can detect unauthorized activity and potential attacks from traffic blocked by Illumio segmentation policy on workloads in "Enforcement" mode. Additionally, the Illumio App for Splunk provides visibility into potentially blocked traffic for workloads in "Test" mode. SOC staff can quickly pinpoint potential attacks and identify workloads with a significant number of blocked flows.  

### Version - 4.1.2  

**Supported Splunk versions**  
* 10.2.x
* 10.1.x
* 10.0.x
* 9.1.x
* 9.0.x

**Supported versions of the Illumio Policy Compute Engine (PCE)**  
* Illumio SaaS PCE (latest)
* 25.2.x
* 24.2.x
* 23.5.x
* 23.2.x
* 22.5.x

**Supported Splunk Common Information Model (CIM) versions**  
* 6.x
* 5.x

## Prerequisites  

* The [**TA-Illumio**](https://splunkbase.splunk.com/app/3657) add-on is required for field extractions and data collection
    * At least one `illumio` modular input must be configured to pull necessary data from the Illumio PCE
* Syslog events must be forwarded to Splunk from the Illumio PCE. See the [TA-Illumio](https://splunkbase.splunk.com/app/3657) documentation for instructions to configure event forwarding for on-prem and SaaS PCEs

### Splunk Architecture  

The Illumio Splunk integration is distributed in two parts:

1) The [**TA-Illumio**](https://splunkbase.splunk.com/app/3657) add-on, which collects and parses syslog events and static objects from the PCE
2) This [**IllumioAppForSplunk**](https://splunkbase.splunk.com/app/3658) app, which visualizes data from the PCE in Splunk dashboards and provides the `Illumio` data model to improve search performance

The app can be installed in either a standalone or distributed Splunk environment.  

> [!NOTE]
> Recommendations for the configuration and topology of a distributed Splunk environment are outside the scope of this document. See the documentation on [Splunk Validated Architectures](https://docs.splunk.com/Documentation/SVA/current/Architectures/Introduction) for suggestions on topology for distributed deployments.  

For a standalone deployment, install and configure the TA per the installation instructions on Splunkbase, and install the app as described in the [Installation](#installation) section below.  

For a distributed environment, install the TA to a heavy forwarder, to an indexer/indexer cluster, or to a search head/search head cluster. Install the app to the search head/search head cluster.  

## Installation  

**Splunk UI**  

1. In the Splunk UI, navigate to the "Manage Apps" page via the Apps drop-down in the top-left, or by clicking the Gear icon next to "Apps" on the Splunk homepage
2. Click the **Browse More Apps** button, and search for `IllumioAppforSplunk`
3. Click **Install**
4. Enter your Splunk login credentials when prompted, then click **Agree and Install**
5. When prompted, restart Splunk

**Splunkbase download**  

1. Navigate to the [**Illumio App for Splunk**](https://splunkbase.splunk.com/app/3658) app in Splunkbase
2. Log in using your Splunk credentials
3. Click **Download** 
4. Read through and accept the EULA and Terms and Conditions, then click **Agree to Download**
5. Transfer the downloaded `.tgz` or `.spl` file to the Splunk server
6. Install the app manually:

using the Splunk binary  

```sh
$SPLUNK_HOME/bin/splunk install app /path/to/IllumioAppforSplunk.spl
```

OR by extracting directly under `/apps`  

```sh
tar zxf /path/to/IllumioAppforSplunk.spl -C $SPLUNK_HOME/etc/apps/
```

7. Restart Splunk

### Configuration  

**Create an index for your Illumio events**

> [!NOTE]
> This is an optional, but recommended, step. If one or more indexes were already created when configuring the TA-Illumio add-on, skip this step.

1. Navigate to Settings -> Indexes
2. Click the **New Index** button in the top-right
3. Enter an index name and select **Illumio App for Splunk** from the App dropdown menu
4. Set the other index parameters based on your expected event volume and retention policy
5. Click **Save**

> [!NOTE]
> Make sure to configure the index based on your organization's compliance requirements and data retention policies. See the Splunk documentation on [configuring index retirement and archiving policy](https://docs.splunk.com/Documentation/Splunk/9.1.1/Indexer/Setaretirementandarchivingpolicy) for more details.

**Update the *illumio_get_index* macro**

1. Navigate to Settings -> Advanced Search -> Search Macros
2. Select **Illumio App for Splunk** from the App dropdown menu
3. Click the `illumio_get_index` macro name to open the edit form
4. Update the definition to reference one or more indexes. For example, `(index="illumio_pce1" OR index="illumio_pce2")`
5. Click **Save**

**Accelerate the Illumio data model**

This is an optional, but recommended, step. See the [data model acceleration](#data-model-acceleration) section below for more details.  

**Install the Sankey Diagram app**

The **Traffic Explorer** dashboard renders traffic flows using the [Sankey diagram custom visualization app](https://splunkbase.splunk.com/app/3112). The app is required for the panel to be displayed, but is otherwise optional.  

## Upgrade Steps  

After upgrading the app through the Splunk UI or manually by following the steps above, follow any additional steps below for the updated version.  

### v3.2.x to >= v4.0.0  

> [!IMPORTANT]
> Make sure that the [**TA-Illumio**](https://splunkbase.splunk.com/app/3657) add-on is installed and upgraded to v4.0.0 before upgrading the app.

1. Disable **Illumio** data model acceleration
2. Back up and remove the following configuration files from `$SPLUNK_HOME/etc/apps/IllumioAppforSplunk/local`:
    * `datamodels.conf` - the **Illumio** data model has been completely changed and is incompatible with previous versions of the app. Any configured acceleration, field overrides or additions, and other changes to the model will need to be removed and re-applied to the updated model
    * `savedsearches.conf` - alert configurations, report schedules, and other overrides to saved searches should be re-applied after reviewing changes to the default saved searches in the app
    * `macros.conf` - the Alert Configurations page and its related macros have been removed in v4.0.0
    * `/data/` - any custom data models, dashboards and views will need to be updated to use the new event structure and field extractions
    * **keep other custom configurations (`indexes.conf`, `inputs.conf`) as-is**
3. Restart Splunk
4. Navigate to `https://your.splunk-server.com/en-US/_bump` to increment the internal version and refresh the static file cache
5. Reconfigure the `illumio_get_index` macro to reference the index or indexes Illumio events are written to
6. Optionally re-enable acceleration on the **Illumio** data model (see the [Data Model](#data-model) section below)
7. Re-apply custom configuration, updating searches to work with the v4.0.0 data model and event structure

### v3.2.0 to v3.2.1  

* The **Illumio** data model needs to be rebuilt after upgrading the app. Refer to the [Data Model Acceleration](#data-model-acceleration) section below.

> [!NOTE]
> **For SaaS PCE users:** If the "Illumio_PCE_Health_Alert" is enabled, it will need to be reconfigured.

### <= v2.3.0 up to v3.2.0  

* The **Illumio** data model needs to be rebuilt after upgrading the app. Refer to the [Data Model Acceleration](#data-model-acceleration) section below.

## Custom Roles  

* `illumio_quarantine_workload` - this custom role must be assigned for a user to trigger the `illumio_quarantine` action. More details about this action can be found in the [TA-Illumio](https://splunkbase.splunk.com/app/3657) documentation

## Alerts  

The Illumio App for Splunk has two scheduled alert saved searches configured but disabled by default. The **Illumio_Check_PCE_Collector_Data** and **Illumio_VEN_Inactivity_Timer_Alert** alerts can be configured and updated as needed:  

1. Navigate to Settings -> Searches, reports, and alerts
2. Select **Illumio App for Splunk** from the App dropdown menu
3. Select **All** or **Nobody** from the Owner dropdown menu
4. In the **Edit** dropdown under Actions for the desired alert search, click **Edit Schedule**
5. Toggle the **Schedule Report** flag on, and set the schedule and dispatch time range for the alert
6. Set one or more actions to occur when the alert is triggered, such as sending an email or Slack message
7. Click **Save**

**Alert Examples**  

The following searches show how Illumio event data can be used to configure custom alerts for common issues. See the Illumio documentation on [event monitoring best practices](https://docs.illumio.com/core/23.2/Content/Guides/events-administration/events-described/events-monitoring-best-practices.htm) for suggestions of events and PCE behaviour to monitor.  

***Workloads affected by policy change*** - monitor security policy changes for high numbers of workloads affected by a single change:  

```
`illumio_get_index` sourcetype="illumio:pce" event_type="sec_policy.create" resource_changes{}.changes.workloads_affected.after > 50
```

The threshold of 50 in the search above can be adjusted based on the number of workloads and overall policy churn in the PCE.  

***Workload modified with specific label*** - monitor workload change operations for specific labels:  

```
`illumio_get_index` sourcetype="illumio:pce" event_type="workload.*" (resource_changes{}.changes.labels.created{}.value="Quarantine" OR resource_changes{}.changes.labels.deleted{}.value="Quarantine")
```

One or more label values that represent high-value applications or zones, such as a Production environment or a customer database, can be monitored to send an alert whenever a workload with those labels is modified.  

***System warnings and errors*** - monitor system health events for warning or higher severity messages:  

```
`illumio_get_index` sourcetype="illumio:pce:health" (sev="warn*" OR sev="err*" OR sev="fatal")
```

Set a relatively high threshold and send an alert if the number of system warnings and errors spikes on the PCE.  

## Saved Searches  

The Illumio App for Splunk provides the following saved searches:

| Search Name                            | Type             | Schedule     | Auto-summary Schedule | Auto-Summary Range         | Description                                           | Enabled by Default |
| -------------------------------------- | ---------------- | -----------: | --------------------: | -------------------------: | ----------------------------------------------------- | ------------------ |
| **Illumio_Auditable_Events**           | scheduled report | */15 * * * * | 55 0 * * 0            | -1w -> now                 | used to summarize auditable events                    | yes                |
| **Illumio_PortScan_Traffic**           | scheduled report | */20 * * * * | 55 1 * * 0            | -1w -> now                 | used to summarize possible instances of port scanning | yes                |
| **Illumio_PortScan**                   | search           | -            | -                     | -                          | uses the **illumio_port_scan_settings_lookup** and the **Illumio_PortScan_Traffic** summary to identify instances of port scanning above the thresholds configured in Illumio modular inputs | yes |
| **Illumio_Firewall_Tampering**         | scheduled report | */15 * * * * | 55 2 * * 0            | -1w -> now                 | used to summarize firewall tampering events           | yes                |
| **Illumio_Check_PCE_Collector_Data**   | scheduled alert  | */5 * * * *  | -                     | -                          | raised if no events from the PCE have been indexed in the dispatch time range | no |
| **Illumio_VEN_Inactivity_Timer_Alert** | scheduled alert  | */5 * * * *  | -                     | -                          | raised if one or more VEN suspend events are reported by the PCE in the dispatch time range | no |

## Data Model  

The Illumio App for Splunk provides an **Illumio** data model that can help to improve search performance at the cost of disk space by building a limited index of PCE syslog event fields.

The model provides the following objects:

| Name                     | Type             | Parent     | Base Search                                                  | Description                     |
| ------------------------ | ---------------- | ---------- | ------------------------------------------------------------ | ------------------------------- |
| **Audit**                | root event node  | -          | `` `illumio_get_index` sourcetype="illumio:pce" ``           | auditable syslog events         |
| **Traffic**              | root event node  | -          | `` `illumio_get_index` sourcetype="illumio:pce:collector" `` | traffic flow events             |
| **Status**               | root event node  | -          | `` `illumio_get_index` sourcetype="illumio:pce:health" ``    | system health and status events |
| **Status.Policy**        | child event node | **Status** | `` event_source="policy" ``                                  | policy service events           |
| **Status.Collector**     | child event node | **Status** | `` event_source="collector" ``                               | collector service events        |
| **Status.FlowAnalytics** | child event node | **Status** | `` event_source="flow_analytics" ``                          | flow_analytics service events   |

> [!NOTE]
> Per Splunk app guidelines, model acceleration is **disabled** by default

**Using the Data Model**

Illumio data model nodes can be referenced using the [**tstats** command](https://docs.splunk.com/Documentation/Splunk/9.1.1/SearchReference/Tstats). For example, the following search uses the **Traffic** node to sum flow counts from a given PCE over time by source/destination IP:

```
| tstats sum(Traffic.count) AS flows FROM datamodel=Illumio.Traffic WHERE Traffic.pce_fqdn="my.pce.com" BY Traffic.timestamp, Traffic.src_ip, Traffic.dest_ip
```

### Data Model Acceleration  

> [!NOTE]
> Enabling/disabling acceleration for the Illumio data model requires the `accelerate_datamodel` capability

To enable acceleration:

1. Navigate to Settings -> Data models
2. Select **Illumio App for Splunk** from the App dropdown menu
3. Click the **Edit** dropdown under Actions for the **Illumio** data model
4. Click **Edit Acceleration**
5. Check the **Acceleration** toggle in the dialog and adjust the Summary Range and advanced settings as needed. See the Splunk documentation on [data model acceleration](https://docs.splunk.com/Documentation/Splunk/9.1.1/Knowledge/Acceleratedatamodels) for a more detailed explanation of the individual parameters for configuring acceleration
6. Click **Save**. It may take quite a bit of time to build the summary for the accelerated model - the progress can be seen under the **ACCELERATION** section after clicking the caret to the left of the model name

> [!NOTE]
> If using a distributed search head cluster, see the Splunk documentation on [sharing data model acceleration summaries](https://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Sharedatamodelsummaries) to avoid rebuilding the summary on each search head in the cluster

**Rebuilding the Data Model**  

To rebuild the summary for the data model:

1. Navigate to Settings -> Data models
2. Select **Illumio App for Splunk** from the App dropdown menu
3. Click the caret to the left of the **Illumio** data model name
4. Click **Rebuild** under the **ACCELERATION** section

## Known Issues  

* The `PCE Operations` dashboard will not be populated for SaaS customers as PCE system health information is not available
* Label Groups are not currently imported by the Illumio Technical Add-On

## Troubleshooting  

> [!IMPORTANT]
> Make sure the [TA-Illumio](https://splunkbase.splunk.com/app/3657) add-on is installed and configured. See the TA documentation for additional troubleshooting steps related to data ingestion and the Illumio modular input

If the app dashboards are not being populated:  

* Check that the `illumio_get_index` macro has been set and make sure it points to the correct index
* Make sure that the configured index or indexes contain data within the given time range
    * To check this, run the following search:

    ```
    `illumio_get_index` | stats count by sourcetype
    ```

    The results should contain one or more sourcetypes with their respective event counts
* Check if the search time range extends further back than the index retention policy
* Check that you aren't hitting your Splunk license limits

If dashboards or visualizations appear to load incorrectly or behave in unexpected ways:  

* Try to clear the static cache using your Splunk instance's `https://my.splunk.com/en-US/_bump` endpoint

If dashboard visualizations are slow to load or searches are delayed:  

* Try reducing the time range of the search
* Enable acceleration for the `Illumio` data model (see [Data Model Acceleration](#data-model-acceleration) above)
* Check if searches are lagging or being delayed due to other jobs or processes running in the background
* Check if the time range your search is being run in accesses cold buckets in your index
    * If your daily data volume is high, you may need to increase the `maxWarmDBCount` in `indexes.conf` to delay the roll-over from warm to cold
* Increase the compute resources allocated to your Splunk instance or cluster

## Uninstalling  

To uninstall the Illumio App for Splunk, follow these steps:  

1. Access the filesystem of the Splunk server where the app is installed 
2. Navigate to `$SPLUNK_HOME/etc/apps`
3. Remove the `IllumioAppforSplunk` folder and all of its contents
4. Restart Splunk

## Release Notes  

### Version 4.1.0

* Illumio App for Splunk & Illumio Technology Add-On for Splunk apps are now Splunk 10 compatible. 
* illumio_quarantine command has been fixed for both Splunk Enterprise and Splunk Cloud.
* Traffic Explorer is now updated to use with Dashboard Studio.
* All python scripts in TA have been updated to use Python 3.9.
* Any missing src_labels & dst_labels in PCE traffic events will be default to "-".

### Version 4.0.1  

* Removed `illumio_quarantine` role definition - it has been moved to TA-Illumio in v4.0.1
* Fixed overly-broad bucketing for some visualizations using accelerated tstats searches
* Removed **Managed Workloads by Enforcement Mode** panel from the Workload Operations dashboard as it duplicated the **Policy Enforcement Mode** panel on the Workload Investigation dashboard
* Updated the **Flows by Policy Decision** panel on the Traffic Explorer dashboard to show both port and protocol. Drilldown now sets both filters on click

### Version 4.0.0  

**New Features**  

* Added support for label types beyond the default RAEL dimensions
* The app now seamlessly supports inputs for multiple PCEs as well as multiple organizations within the same PCE cluster
* A custom script, `resubmit_click_handler.js`, has been added. It is used on the `Change Monitoring` and `Traffic Explorer` dashboards to automatically update searches when a token-set drilldown is clicked

**Improvements**  

*Data model and Searches*

* The Illumio datamodel has been updated and no longer uses the Illumio.Illumio root node. It is replaced by three root event nodes for the `illumio:pce`, `illumio:pce:collector`, and `illumio:pce:health` sourcetypes. See the [Data Model](#data-model) section above for further details
* The `Illumio_PortScan` saved search has been split into a summary search (`Illumio_PortScan_Traffic`) and a filtering search (`Illumio_PortScan`). It now requires `pce_fqdn` and `org_id` values to be passed as parameters: ```| savedsearch Illumio_PortScan pce_fqdn="my.pce.com" org_id=1```

*Dashboards*  

* Search performance on dashboards has been significantly improved
* Dashboard searches have been overhauled to use KV Store lookups for PCE metadata objects where appropriate
* Role/App/Environment/Location label filters have been removed from dashboards and replaced with a single multivalue filter for all label dimensions
* Dashboards other than **PCE Operations** now provide an **Org ID** filter
* **Change Monitoring**
    * Removed Daily Changes/Creates/Updates/Deletes panels in favour of single **Total Changes** chart
    * Simplified searches and drilldowns
    * Added a **Latest Policy Changes** view showing changes in the most recent security policy create events
* **Traffic Explorer**
    * Changed to a single base tstats search to improve performance
    * Added filters for both source and destination labels and hostname/IP
* **PCE Operations**
    * Removed custom javascript and changed to trellis searches for viewing cluster host status
    * Added warning/critical thresholds to PCE status charts
* **Security Operations**
    * Simplified dashboard 
* **Workload Operations / Workload Investigation**
    * Dashboard use the `illumio_workloads_lookup` to improve performance and simplify searches

*QoL*  

* `illumio.xml` has been renamed to `security_operations.xml` to better reflect the dashboard it represents
* The incorrect spelling `Firewall Tempering` has been corrected to *Tampering* in all locations
* All dashboards now use a Submit button instead of submit-on-change

**Removed Features**  

* All custom javascript from previous versions of the app have been removed
* All KVStore collections in the app have been removed. Mapping lookups are superseded by their new counterparts in the Illumio TA, and the static CSV lookups have been changed to fixed values in the relevant dashboards
* The **Alert Configurations** page has been removed - these custom alerts had limited usefulness; similar searches to create custom alerts can be found in the [alerts](#alerts) section above
* The **Alerts** link has been removed - this was an unnecessary redirect to the alert settings page
* The following macros have been removed:
    * `illumio_get_time(1)` - the searches on the Security Operations dashboard using this macro have been changed
    * `illumio_portscan_index` - port scan data is no longer summarized to this index
    * `illumio_system_health`, `illumio_rule_update`, `illumio_policy_provisioning`, `illumio_workload_labeling` - these were set using the now-removed **Alert Configurations** page
* All outputlookup saved searches have been removed: `Illumio_Workload_Mapping`, `Illumio_IP_Lists_Mapping`, `Illumio_Services_Mapping`, `Illumio_PortScan_Details`, `Illumio_Host_Details`, `Illumio_Host_Details_S3`, and `Illumio_hostname_ip_mapping` are superseded by the updated PCE metadata KVStore collections in the Illumio TA
* The Supercluster **leader_fqdn** token has been removed from all dashboards and searches

### Version 3.2.1  

* Added support for SaaS PCE.

### Version 3.2.0  

* Added below dashboards:
    1) PCE Authentication Events
    2) Traffic Explorer
    3) Change Monitoring
* Added below panels in PCE Operations (On-Prem Only) dashboard:
    1) Data Ingestion Volume In The Last Day
    2) Data Ingestion Volume In The Last 30 Days
* Updated below panels in Workload Investigations dashboard.
    * Removed Traffic Events panel.
    * Added Active VEN, Suspended VEN, Stopped VEN, Policy Enforcement State and Policy Synchronization Status panels.
    * Added Status, Severity and Notification Type filter to the Audit Events panel.
* Added "Unknown" option on "Security Operations" dashboard's "Traffic" filter.
* Fixed disk latency issue in "PCE Operations (On-Prem Only)" dashboard's "Cluster Cores" Panel.
* Bundled the jQuery3 in the app package.
* Added "Supercluster Leader" filter to all dashboards.
* Added "illumio_portscan_index" macro to summarize port scan data to custom index.
* Modified "Illumio_Workload_Mapping" savedsearch so that it clears records older than 30 days in "illumio_workload_mapping_lookup" lookup.

### Version 3.1.0  

* Added below panels in PCE Operations dashboard: 
    1) VEN Heartbeat Latency
    2) VEN Policy Latency
    3) Collector Flow Rate 
    4) Traffic Ingest Rate
    5) Policy Database Summary
    6) Disk Latency in Cluster Cores Section
* Used Basesearch for panels in PCE operations dashboard to improve search performance.

### Version 3.0.0  

* Splunk 8 Support.
* Made App Python23 compatible.
* Changed all queries to datamodel for sourcetype "illumio:pce".
* Added label filters on Workload Investigation.
* Added Allowed option on Security Operations.

### Version 2.3.0  

* Added Alert Configuration screen to create/update alert filters.
* Workload Investigation: Added drilldown from panel Audit Events.
* Added support of S3 collected data.

### Version 2.2.1  

* Fixed the bug with Quarantine workload from the drill-down of Firewall Tampering panel.
* Panels using Syslog data, now use pce_fqdn field instead of fqdn field.
* Auditable event count uses both system events and audit events.
* In Workload Operations dashboard, changed default time range from 60 minutes to 72 hours.
* Added 'PCE' column in the drill-down of Firewall Tampering panel.
* Removed "Illumio_Host_PublicIP_Mapping" and "Illumio_PublicIP_Host_Mapping" saved searches as we are not using host field anymore inside "illumio_host_details_lookup".

### Version 2.2.0  

* Created new dashboard "Workload Investigation".
* Created new panels "VEN Count", "VEN Event Count By Status", "Agent Event Count By EventType" and "Workload Event Count By EventType" in "Workload Operations" dashboard.
* Modified panels "Managed VEN by Version", "Managed VEN by Mode" and "Managed VEN by Operating System" in "Workload Operations" dashboard.
* Updated the logic of "Port Scan" panel.
* Removed "dnslookup" custom command.

### Version 2.1.0  

* Added support of Illumio PCE 18.3.1, 19.1
* Updated the search time of single value panels to last 60 minutes with trend line of 24 hours in Security Operations dashboard.
* Fixed the bug related to "unknown" or "NULL" legend in "Top Workloads with" and "Managed VEN by Operating System" panels.
* Fixed the bug related to label filter not considering label type while searching for traffic data in Security Operations dashboard.

### Version 2.0.2  

* Added support of Illumio PCE 18.2.1, 18.2.2, 18.2.3

### Version 2.0.1  

* Removed VEN Changes by Type panel from Workload Operations dashboard.

### Version 2.0.0  

* This version of App is only compatible with Illumio PCE 18.2.0
* This version of App is not compatible with Illumio PCE 17.X

## EULA  

See the EULA document on the [Illumio Integrations docs site](https://docs.illumio.com/LandingPages/Categories/illumio-integrations.htm).  

## Support  

* Access questions and answers specific to Illumio App for Splunk at https://answers.splunk.com.
* Support Offered: Yes
* Support Email: app-integrations@illumio.com
* Please visit https://answers.splunk.com, and ask your question regarding Illumio App for Splunk. Please tag your question with the correct App Tag, and your question will be attended to.

## License  

Copyright 2023 Illumio, Inc. All rights reserved.  

```
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
```
