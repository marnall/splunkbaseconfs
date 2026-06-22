Cylana Splunk Add-on 

Overview
The Cylana Splunk Technology Add-on enables ingestion and parsing of Cylana security telemetry within the Splunk platform.

Cylana is an external attack surface management (EASM) and cyber threat intelligence platform that detects security threats such as phishing domains, brand impersonation attempts, exposed assets, and other external risk indicators.

This add-on provides field extraction and normalization for Cylana events, allowing Splunk users to search, analyze, and visualize Cylana security data using native Splunk search capabilities and dashboards.

The add-on supports structured JSON event ingestion via Splunk's HTTP Event Collector (HEC).

Features
- Native parsing of Cylana security telemetry
- Automatic JSON field extraction
- Support for multiple Cylana event types
- Compatible with Splunk Search & Reporting
- Enables threat hunting and security analytics using Cylana data
- Lightweight Technology Add-on with no external dependencies

Supported Sourcetypes
The following Cylana sourcetypes are supported:

cylana:alert
cylana:indicator
cylana:asset
cylana:exposure

These sourcetypes represent different types of Cylana security telemetry including threat alerts, threat intelligence indicators, monitored assets, and exposure findings.

Installation
1. Download the TA_cylana package from Splunkbase.
2. Install the add-on on the Splunk Search Head or Indexer.
3. Restart Splunk after installation.

Example installation path:

$SPLUNK_HOME/etc/apps/TA_cylana

Configuration
The Cylana Splunk Add-on does not require additional configuration within Splunk.

Cylana events should be sent to Splunk using HTTP Event Collector (HEC) with the appropriate sourcetype.

Example configuration:

sourcetype = cylana:alert
index = cylana

Data Ingestion
Cylana security events are typically forwarded to Splunk via HTTP Event Collector (HEC) in JSON format.

Example Cylana alert event:

{
  "event_type": "alert",
  "brand": "Akbank",
  "indicator": "odeme-akbank-dogrulama.com",
  "severity": "critical",
  "risk_score": 95,
  "category": "phishing",
  "confidence": "high",
  "asset": "akbank.com",
  "detection_source": "screenshot_similarity"
}

Once ingested, fields are automatically extracted using Splunk's JSON parsing capabilities.

Example Searches

Top targeted brands:

index=cylana sourcetype=cylana:alert
| stats count by brand
| sort -count

Alert severity distribution:

index=cylana sourcetype=cylana:alert
| stats count by severity

Recent Cylana alerts:

index=cylana
| table _time brand indicator severity risk_score category confidence asset
| sort -_time

Compatibility
This add-on has been tested with:

- Splunk Enterprise
- Splunk Cloud Platform
- Splunk Search & Reporting

Support
For questions or support related to Cylana integrations, please contact the Cylana team.

Author
Cylana

Maintainer
Onur Cabik

License
Copyright © Cylana
All rights reserved.
