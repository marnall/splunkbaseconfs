# Performance Insights for Splunk

The Performance Insights App provides Splunk Enterprise customers an aggregated view into all things related to performance. Through its dashboards, you can monitor daily ingest volumes by source types, search performance, Data Model Acceleration performance, CPU and memory usages by component. You can spot trends in performance over time and take action early to resolve potential outages. The App is designed by using the Splunk APIs on internal Splunk logs so you can easily modify it to serve your needs.

### The App includes

- A dashboard with data reports, performance insights with different ranges of real-time visibility.
- Discover and store key states information of data sources, data hosts and metric hosts availability.
- Analyse and detect lack of data and performance lagging of data sources and hosts within your Splunk deployment
- Visibility on overall performance trends with a high-level overview of data load, search metrics, and resource utilization.
- Centralized information on system and data configuration, looking at machine specs, installed apps, ingestion sourcetypes, pipelines, and more.
- Key performance indicators of various Splunk Enterprise features like Smart Store, rolling restarts, bundle replication, and more.
- A page dedicated to diagnosing errors and warnings on the system.

### Release Notes

#### v1.1.2

- Removed dependency on 'tabs.js', which fixes the javascript error on newer SE versions.
- Introduces base searches for similar searches for CPU use reduction.
- Moved results from frequently used REST API searches into tokens for CPU use reduction.
- Fixed broken charts.
- Removed dependency on risky functions, which removes need to explicitly allow some charts to run.
- Added chart granularity control.
- Cleaned up messy charts.
- Fixed skipped search reporting errors.

#### v1.1.3

- Added support for multiple search head clusters.

#### v1.1.6

- Fixed granularity filter overwrite on page refresh.
- Fixed On Prem search head filter error.

#### v1.1.7

- Added failure counting in addition to the existing skipped search counts.
- Added a user limits tab to the Resource Monitoring dashboard.

### Support

Support is provided on a "best effort" basis only at PerfInsights@splunk.com.

