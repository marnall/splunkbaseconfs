# Upstream App for Cybersecurity Alerts

## Overview

This app provides dashboards for monitoring and analyzing vehicle cybersecurity
alerts ingested from the Upstream Security platform into Splunk.

### Dashboard Tabs

- **INSIGHTS**: Geographic alert map, severity breakdown pie chart, alert trends
  over time, and top alert categories.
- **ALERTS**: Detailed alert table with time, name, detector type, country,
  vehicle model, and severity. Supports drill-down into individual alerts.

## Prerequisites

- Splunk Enterprise 8.0+ or Splunk Cloud
- The Upstream Security Add-on for Cybersecurity Alerts (TA-upstream) v1.0.12+
  must be installed and configured to ingest alerts into the "main" index.

## Installation

1. Install via "Manage Apps" > "Install app from file" in Splunk Web,
   or extract the package to $SPLUNK_HOME/etc/apps/.
2. Ensure TA-upstream is installed and actively ingesting data.
3. Navigate to the app to view your alerts dashboard.

## Support

Contact Upstream Security at support@upstream.auto for assistance.

