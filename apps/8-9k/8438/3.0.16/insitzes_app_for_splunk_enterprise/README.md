The InSitzes App for Splunk Enterprise Monitoring provides administrators with actionable insights into ingestion, performance, workload, and search behavior across their Splunk Enterprise environment. By consolidating system, data, and workload visibility into one app, it enables teams to proactively detect issues, optimize resource usage, and improve the overall Splunk Enterprise experience.

The InSitzes App delivers a comprehensive monitoring suite for Splunk Enterprise, giving admins and power users transparency into how their environment is running and being used. With dedicated tabs for health, ingestion, system, forwarding, data quality, search, workload, dashboards, and compute, the app helps identify bottlenecks, validate data quality, and highlight optimization opportunities.

This app is designed to answer the most critical Splunk Enterprise monitoring questions:

- Is my environment healthy and are there any critical issues I need to address?
- Is my data flowing reliably and without gaps?
- Are searches running efficiently and fairly across workloads?
- Which dashboards or searches are creating bottlenecks?
- Am I approaching my license quota?
- What would my workload cost under Splunk Cloud compute-based licensing?

## Feature Breakdown

### Health
Get an at-a-glance view of your entire Splunk Enterprise environment health. This tab runs 31 automated checks across 8 categories including ingestion, data quality, search, forwarding, system, compute, workload, and capacity. Each check is assigned a weighted severity (critical, high, medium, or ok) and rolled up into an overall health score percentage. Use this tab as your starting point to quickly identify areas that need attention before drilling into the detailed tabs.

Health checks include:
- **System**: Splunkd log health, apps requiring updates, indexer/search head CPU & memory
- **Ingestion**: Volume anomaly detection (index & sourcetype), ingestion latency, last chance index events, event timestamp quality
- **Data Quality**: Parsing issues, debug event detection
- **Search**: Long running searches, large lookup files, redundant searches, skipped/failed scheduled searches, zero result scheduled searches, search concurrency, search criticality, data model acceleration health
- **Compute**: SVC utilization, SVC attribution
- **Workload**: WLM aborted/reclassified searches
- **Forwarding**: Queue blocking events, indexing queue fill
- **Capacity**: Index governance

### Ingestion
Gain visibility into data flow health across indexes and sourcetypes. Detect anomalies such as unexpected data spikes or drops that could signal data loss, ingestion delays, or license risks. Monitor license usage against your daily quota with a 7-day usage history trend. Ingestion data is read live from the `_internal` license_usage events so there is no scheduled lookup to maintain, which also means dashboards reflect the most recent hour of activity without backfill. This helps administrators take proactive action before downstream searches or alerts are impacted.

### System
Monitor the underlying health of your Splunk Enterprise environment, including CPU, memory, and disk utilization across all server roles: search heads, indexers, cluster manager, deployment server, and SHC deployer. Track server status, app/add-on versions, and splunkd error rates. Identify system bottlenecks and resource constraints that may degrade user experience or cause search slowdowns.

### Forwarding
Track the health and throughput of forwarders sending data to Splunk Enterprise. Detect queue build-ups, blocked pipelines, or uneven load distribution. Monitor HEC performance, deployment client activity, data flow patterns, and SSL/connection issues, ensuring that critical data makes it into your environment reliably and on time.

### Data Quality
Detect and resolve issues with event structure, timestamps, and field extractions. This tab surfaces sourcetypes with parsing issues, missing props configurations, timestamp/timezone problems, and excessive debug events. It helps ensure that indexed data is reliable, searchable, and aligned to Splunk data quality best practices.

### Search
Measure how searches are executing across your Splunk Enterprise stack. Track scheduled search execution and skip rates, identify large lookup files, wasteful and redundant scheduled searches, and dispatch runtime delays. Monitor zero-result scheduled searches that scan data without returning results, and track search concurrency limits. This tab helps pinpoint inefficient queries or high-demand workloads impacting user experience.

### Workload
Gain deep visibility into how search workloads are governed and executed in Splunk Enterprise. This tab highlights:

- **Filtered/Reclassified/Aborted Searches** -- Understand when workload management rules are filtering, reclassifying, or aborting searches to control concurrency and protect system stability.
- **Search Runtimes** -- Identify long-running or resource-intensive searches that may cause bottlenecks, with detailed breakdowns by search type and user.

With these insights, administrators can fine-tune workload management policies, ensuring high-priority searches execute reliably while keeping resource contention under control.

### Dashboards
Understand the impact of dashboards on your Splunk Enterprise resources. This tab provides:

- **Dashboard Refresh Monitoring** -- See how many dashboards exist and how frequently they refresh across Simple XML panel refreshes, Simple XML full refreshes, and Dashboard Studio refreshes.
- **Base vs. Chain Search Analysis** -- Gain visibility into dashboards using base searches versus chained searches, helping uncover opportunities to consolidate or optimize searches.

With these insights, administrators can reduce simultaneous search execution, optimize dashboard design, and improve performance for end users.

### Compute
Get a comprehensive view of estimated Splunk Virtual Compute (SVC) consumption based on CPU-proportional attribution from introspection data. This tab helps enterprise administrators understand what their workload would cost under Splunk Cloud compute-based licensing. SVC estimates are computed hourly by the `insitzes_svc_estimation` saved search using `_introspection` data with dynamic role discovery via `| rest /services/server/roles`.

SVC Estimation Breakdown:
- **Estimated Compute (24h)** -- Total estimated SVC consumption over the last 24 hours.
- **By Search Head** -- Understand which search heads are driving the most load.
- **By App** -- Identify applications consuming the bulk of resources.
- **By Search Type, Label & Provenance** -- Distinguish between scheduled, ad-hoc, and dashboard searches and trace consumption to its source.
- **By User** -- See which users are generating the most SVC usage.
- **Consumer Breakdown** -- View compute allocation across search, data services, and shared services.
- **Cost Modeling** -- Toggle to cost mode and enter a per-unit price to see estimated costs across all dimensions.

## Saved Searches & Lookups

The app includes a scheduled saved search that collects and pre-computes data for efficient dashboard rendering:

| Saved Search | Schedule | Description |
|---|---|---|
| `insitzes_svc_estimation` | Every hour at :10 | Computes SVC consumption estimates from introspection data using dynamic role discovery, appends to a self-pruning 24-hour lookup |

Lookup files:
- `insitzes_svc_estimation.csv` -- Hourly SVC estimation data (24-hour retention)
- `insitzes_config.csv` -- App configuration (deployment type, licensing model, feature toggles)

## Alert Saved Searches

The app includes pre-built alert saved searches (disabled by default) that can be enabled for proactive monitoring:

| Alert | Description |
|---|---|
| `insitzes_monitoring_ingestion_alert_by_idx` | Alerts when any index shows critical ingestion anomalies |
| `insitzes_monitoring_ingestion_alert_by_st` | Alerts when any sourcetype shows critical ingestion anomalies |
| `insitzes_monitoring_app_updates_alert` | Alerts when apps have available updates |
| `insitzes_monitoring_large_lookup_alert` | Alerts when lookup files exceed size thresholds |
| `insitzes_monitoring_redundant_searches_alert` | Alerts when redundant scheduled searches are detected |
