# Trend Micro TippingPoint Threat Protection System Splunk Add-on

## Overview
The **Trend Micro TippingPoint Threat Protection System (TPS) Splunk Add-on** enables Splunk to ingest and parse security event data from the TippingPoint TPS in **Common Event Format (CEF)**. This add-on helps security teams monitor and analyze threat data within Splunk for improved threat detection and response.

## Features
- Supports ingestion of CEF-formatted logs from TippingPoint TPS.
- Extracts and normalizes key security fields for efficient search and analysis.
- Maps extracted data to Splunk's **Common Information Model (CIM)** for compatibility with Splunk Enterprise Security (ES).
- Provides pre-built field extractions, event types, and tags for better correlation.
- The default sourcetype is `tippingpoint`, and the add-on includes a **sourcetype changer** that checks for CEF format and rewrites the sourcetype to `tippingpoint:cef`. Ensure proper configuration to leverage this feature.

## Prerequisites
- Splunk Enterprise 8.2 or later.
- Splunk Universal Forwarder (if collecting logs from a remote source).
- Trend Micro TippingPoint TPS configured to send logs in CEF format.

## Installation
1. Download the add-on from **Splunkbase**.
2. Install it on your Splunk instance:
   - For distributed environments, install on **Heavy Forwarders, Indexers, and Search Heads** as required.
3. Restart Splunk after installation.

## Sample Simple Configuration
1. Navigate to **Splunk Web > Settings > Data Inputs**.
2. Configure a new **CEF Syslog** input or use a Splunk Universal Forwarder to receive logs, set sourcetype **tippingpoint**
3. Verify event ingestion using the search query:
   ```
   index=<your_index> sourcetype=tippingpoint:cef
   ```
4. (Optional) Enable CIM mapping for Splunk ES by ensuring correct field extractions.

## Usage
- Use Splunk Search to investigate TippingPoint security alerts:
  ```
  index=<your_index> sourcetype=tippingpoint:cef | table _time signature severity src_ip dest_ip
  ```
- This add-on maps logs to the **Splunk Intrusion Detection (IDS/IPS) data model** to ensure compatibility with **Splunk Enterprise Security (ES)**.
- Integrate with **Splunk Enterprise Security** to create correlation searches and dashboards.

## Support
For issues or feature requests, please contact the add-on developer via Splunkbase or sent an issue or requests via email: splunk@netbytesecurity.com

## License
This add-on is released under the Splunkbase App License.

