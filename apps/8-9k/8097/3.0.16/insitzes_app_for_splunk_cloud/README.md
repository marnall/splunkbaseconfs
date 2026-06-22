The InSitzes App for Splunk Cloud Monitoring provides administrators with actionable insights into ingestion, performance, workload, and search behavior across their Splunk Cloud environment. By consolidating system, data, and workload visibility into one app, it enables teams to proactively detect issues, optimize resource usage, and improve the overall Splunk Cloud experience.

Splunkbase: https://splunkbase.splunk.com/app/8097


The InSitzes App delivers a comprehensive monitoring suite for Splunk Cloud, giving admins and power users transparency into how their environment is running and being used. With 12 dedicated tabs covering health, ingestion, system, forwarding, storage, data quality, search, workload, dashboards, compute, and capacity, the app helps identify bottlenecks, forecast growth, validate data quality, and highlight optimization opportunities.

This app is designed to answer the most critical Splunk Cloud monitoring questions:

Is my environment healthy and are there any critical issues I need to address?
Is my data flowing reliably and without gaps?
Are searches running efficiently and fairly across workloads?
Where are SVCs being consumed and how can usage be optimized?
Which dashboards or searches are creating bottlenecks?
How fast is my storage growing, and do I need to plan for expansion?
Am I using my compute and storage capacity efficiently?

Feature Breakdown

Health
Get an at-a-glance view of your entire Splunk Cloud environment's health. This tab runs 31 automated checks across 8 categories and provides:

Overall Health Score -- A weighted score reflecting the state of your environment (90%+ = healthy).
Issue Severity Breakdown -- Counts of Critical, High, Medium, and OK health check items.
Health Check Details -- A color-coded grid of individual health check results with severity levels.

Health checks include:
- **System**: Splunkd log health, apps requiring updates, indexer/search head CPU & memory
- **Ingestion**: Volume anomaly detection (index & sourcetype), ingestion latency, last chance index events, event timestamp quality
- **Data Quality**: Parsing issues, debug event detection
- **Search**: Long running searches, large lookup files, redundant searches, skipped/failed scheduled searches, zero result scheduled searches, search concurrency, search criticality, data model acceleration health
- **Compute**: SVC utilization, SVC attribution
- **Storage**: DDAS utilization, DDAA utilization
- **Workload**: WLM aborted/reclassified searches
- **Forwarding**: Queue blocking events, indexing queue fill
- **Capacity**: Indexer cache churn, index governance, inefficient dashboards

This tab serves as the recommended starting point, giving administrators a quick summary of what needs attention before diving into specific areas.

Ingestion
Gain visibility into data flow health across indexes and sourcetypes with severity-based ingestion monitoring. This tab categorizes ingestion issues into four severity levels (Low, Medium, High, Critical) and breaks them down by both Index and Sourcetype, making it easy to prioritize which data flow problems need immediate attention. Ingestion data is read live from the `_internal` license_usage events so there is no scheduled lookup to maintain. Detailed ingestion views let administrators drill into specific indexes or sourcetypes to investigate anomalies such as unexpected data spikes or drops that could signal data loss, ingestion delays, or license risks.

System
Monitor the underlying health of your Splunk Cloud environment across all major tiers. This tab provides:

App & Add-On Update Tracking -- Identify apps and add-ons that require updates.
Splunk Errors -- Monitor system-wide error counts.
CPU Utilization -- Track both current and 95th percentile CPU usage across Search Heads, Indexer Clusters, and IDM tiers.
Memory Utilization -- Track both current and 95th percentile memory usage across Search Heads, Indexer Clusters, and IDM tiers.
These per-tier metrics help administrators pinpoint exactly where resource constraints exist and whether issues are sustained or transient.

Forwarding
Track the health and throughput of forwarders and data collection infrastructure. This tab provides:

Data Flow Activity -- Monitor overall data flow and forwarded data volume.
Forwarder Throughput -- Compare forwarder vs. indexer throughput and track average TCP and Splunk version details.
Queue Health -- Detect forwarding blocks by queue type.
HEC Monitoring -- Track HTTP Event Collector request volume and failures.
SSL & Connectivity -- Identify hosts with failed SSL connections, hosts sending non-SSL data, and hosts unable to connect to the Deployment Server.
Deployment Client Details -- View deployment clients by Splunk version and OS.
Last Chance Index Usage -- Detect data routed to unconfigured, disabled, or deleted indexes.
HEC Token Inventory -- Track the number of unique HEC tokens in use.

Ingestion
Analyze indexing pipeline activity with a focus on cache management and queue health. This tab provides:

Indexer Count -- Current number of indexers in the environment.
Cache Churn Analysis -- Track days with cache churn above 5%, daily average cache upload/download volumes, cache churn percentage stats, and estimated cache days.
Cache Activity -- Monitor indexer bucket cache activity and cache downloads by index.
Ingestion Trends -- View indexer ingestion rate trends over time.
Queue Health -- Monitor indexing queue block counts and fill percentage thresholds (>75%).
Performance Correlation -- Analyze indexing performance vs. CPU utilization to identify resource-driven bottlenecks.

Storage
Monitor current storage usage and project future capacity needs for both DDAS (Dynamic Data Active Searchable) and DDAA (Dynamic Data Active Archive) licenses. This tab provides:

Current Utilization -- Real-time license utilization percentages, utilized GB, and licensed capacity for both DDAS and DDAA.
Forecasted Utilization -- Projected utilization percentages, GB usage, and additional license GB needed for both DDAS and DDAA.
Trend Visualizations -- Charts showing DDAS and DDAA usage trends with forecasting.
Data Governance KPIs -- A 7-day assessment of data governance metrics.
SVC Usage -- Splunk Virtual Compute usage overview.
These insights help administrators plan ahead for storage expansion and align capacity with business and compliance requirements.

Data Quality
Detect and resolve issues with event structure, timestamps, and field extractions. This tab provides:

Data Quality Analysis -- Surface issues by sourcetype, identify potential timestamp/timezone problems, and detect debug events in indexed data.
Configuration Viewer -- Inspect props.conf settings for selected sourcetypes.
System Health Indicators -- Monitor compute capacity, search abort rates, active user counts, and Splunk errors.
HEC Traffic -- Track HTTP Event Collector request volume.
App Update Tracking -- Identify apps and add-ons requiring updates.
Resource Utilization -- Current and 95th percentile CPU and memory utilization across Search Head, Indexer Cluster, and IDM tiers.
Storage Forecast -- Forecasted DDAS license utilization percentage.
This comprehensive view helps ensure that indexed data is reliable, searchable, and aligned to Splunk data quality best practices.

Search
Measure how scheduled searches are executing across your Splunk Cloud stack. This tab provides:

Execution Metrics -- Track average hourly scheduled search executions and skipped executions.
Wasteful Search Detection -- Identify potentially wasteful scheduled searches that consume resources without delivering value, including zero-result searches scanning zero buckets.
Large Lookup Analysis -- Surface large lookup files that may impact search performance.
Skip Analysis -- View skipped scheduled search percentages, reasons, and per-app breakdowns with detailed skip information.
Dispatch Delay -- Monitor job dispatch runtime delay at the 95th percentile, with attribution by saved search and user.
Search Type Activity -- See the distribution of search activity by type.
Search Concurrency -- Monitor concurrency limit events and search scheduling pressure.
These insights help administrators identify inefficient queries, resolve scheduling conflicts, and reduce unnecessary search load.

Workload
Gain deep visibility into how search workloads are governed and executed in Splunk Cloud. This tab highlights:

% Filtered Searches -- Understand when admission rules block searches to control concurrency and protect system stability.
% Reclassified Searches -- See how often searches are reassigned to different resource pools by workload rules.
% Aborted Searches -- Track the rate of system-aborted searches.
Search Runtime Summary & Details -- Identify long-running or resource-intensive searches with summary statistics and detailed breakdowns.
Search Head Memory Utilization -- Monitor memory consumption on search heads to detect resource pressure.
With these insights, administrators can fine-tune workload management policies, ensuring high-priority searches execute reliably while keeping resource contention under control.

Dashboards
Understand the impact of dashboards on your Splunk Cloud resources. This tab provides:

Search Abort Rate -- Track the percentage of aborted searches tied to dashboard activity.
Simple XML Panel Refreshes -- Monitor how frequently Simple XML dashboard panels refresh.
Simple XML Full Refreshes -- Track full dashboard refresh frequency for Simple XML dashboards.
Dashboard Studio Refreshes -- Monitor refresh activity for Dashboard Studio dashboards.
Regular vs. Chain Search Analysis -- Compare dashboards using regular searches versus chained searches, helping uncover opportunities to consolidate or optimize.
Large Lookup Files -- Identify large lookup files that may slow down dashboard rendering.
With these insights, administrators can reduce simultaneous search execution, optimize dashboard design, and improve performance for end users.

Compute
Get a comprehensive view of Splunk Virtual Compute (SVC) consumption and the underlying infrastructure health that drives it. This is the most detailed tab in the app, providing visibility across multiple dimensions:

SVC Consumption Breakdown:
Licensed SVCs & Compute Capacity -- View licensed SVC allocation and current capacity utilization with optimal (80%) and degradation (90%) threshold lines.
By Search Head -- Understand which cluster members are driving the most load.
By App -- Identify applications consuming the bulk of resources.
By Search Type, Label & Provenance -- Distinguish between scheduled, ad-hoc, and dashboard searches and trace consumption to its source.
By User -- See which users are generating the most SVC usage.
Consumer Breakdown -- View compute allocation across search, data services, and shared services.
Cost Modeling -- Toggle to cost mode and enter a per-unit price to see estimated costs across all dimensions.

Data Flow & Ingestion:
Data Flow Activity & Forwarded Data Volume -- Monitor ingestion pipeline throughput.
HEC Requests & Failures -- Track HTTP Event Collector health.
SSL & Connectivity -- Identify hosts with failed SSL connections, non-SSL data transmission, and Deployment Server connectivity issues.

Search & Performance:
Job Dispatch Runtime Delay (95th Percentile) -- Monitor search queue latency.
% Filtered Searches -- Track admission rule filtering rates.
Skipped Scheduled Search Details -- View details on searches that failed to execute.
Deployment Client Details -- Track client distribution by Splunk version and OS.

Indexer & Cache Performance:
Archive Storage Capacity -- Monitor archive storage utilization.
Cache Churn & Activity -- Track days with cache churn above 5%, daily cache upload/download volumes, and bucket cache activity by index.
Indexer Ingestion Trends -- View ingestion rate trends over time.
Queue Health -- Monitor indexing queue blocks and fill percentages.
Performance vs. CPU Correlation -- Identify resource-driven indexing bottlenecks.
Coupled with the Dashboards and Search tabs, this view gives administrators a clear path to optimize search patterns, reduce unnecessary consumption, and improve overall Splunk Cloud performance and usability.

Capacity
Get a holistic view of your Splunk Cloud environment's capacity utilization and operational efficiency. This tab provides:

Active User Count -- See how many users are concurrently active.
Efficiency Metrics -- Track average GB/SVC per day to measure how efficiently your environment converts compute resources into data throughput.
Capacity Overview -- Monitor compute capacity, searchable storage capacity, and archive storage capacity as percentages.
Search Abort Rate -- Track the percentage of aborted searches as an indicator of resource pressure.
Dashboard Studio Refreshes -- Monitor Dashboard Studio refresh activity and its impact on capacity.
Ingestion Severity Analysis -- View ingestion issues categorized by severity (Low, Medium, High, Critical) broken down by both Index and Sourcetype.
Splunk Errors -- Track system-wide error counts.
This tab helps administrators understand whether their environment is right-sized and identify areas where capacity adjustments or efficiency improvements are needed.

## Lookups

Lookup files:
- `insitzes_config.csv` -- App configuration (deployment type, licensing model, feature toggles)

## Alert Saved Searches

The app includes pre-built alert saved searches (disabled by default) that can be enabled for proactive monitoring:

| Alert | Description |
|---|---|
| `insitzes_monitoring_ingestion_alert_by_idx` | Alerts when any index shows critical ingestion anomalies |
| `insitzes_monitoring_ingestion_alert_by_st` | Alerts when any sourcetype shows critical ingestion anomalies |
| `insitzes_monitoring_storage_alert` | Alerts when DDAS or DDAA storage utilization exceeds 100% |
| `insitzes_monitoring_app_updates_alert` | Alerts when apps have available updates |
| `insitzes_monitoring_large_lookup_alert` | Alerts when lookup files exceed size thresholds |
| `insitzes_monitoring_redundant_searches_alert` | Alerts when redundant scheduled searches are detected |
