# Ops Pulse

**Version:** 1.1.0  
**Splunkbase Release:** Minor update (UX & internal refactor)

Splunk Ops Pulse is a lightweight, free Splunk app that provides instant operational health, anomaly detection, and degradation visibility for any existing Splunk data — without requiring ITSI, Machine Learning Toolkit, Python, or external integrations.

It is designed for teams that want fast operational insight immediately after data onboarding.

🚀 Why Splunk Ops Pulse?

Many Splunk users face these challenges:

No quick operational visibility after onboarding new data

ITSI is powerful but too heavy or licensed for many environments

No simple, explainable anomaly indicators out of the box

Dashboards show data, but not health or early warning signals

Splunk Ops Pulse solves this by providing:

A simple 0–100 health score

Baseline-based volume anomaly detection

Error spike detection

Slow degradation and early warning indicators

Zero configuration beyond index selection

🧠 Key Features
✅ Operational Health Score

Single numeric score (0–100)

Based on real error rates

Updates dynamically with time range

📊 Event Volume Anomalies

Detects sudden spikes or drops

Uses statistical baselines (avg + stdev)

No static thresholds

🚨 Error Spike Detection

Identifies short-term error explosions

Relative + absolute detection logic

Works on any log data

📉 Degradation & Trend Detection

Rolling error averages

Detects slow failures before incidents

Early warning indicators without ML

🔍 Works on Any Index

Structured or unstructured data

Supports wildcard index selection

No hardcoded index names

🧩 Dashboards Included
1️⃣ Operational Overview

Purpose: At-a-glance system health
Panels:

Health Score

Event Volume vs Baseline

Error Rate Trend

Top Error Hosts

2️⃣ Anomaly Detection

Purpose: Identify abnormal behavior
Panels:

Event Volume Anomalies

Error Spike Detection

Anomalous Time Buckets

3️⃣ Degradation & Trends

Purpose: Detect slow failures
Panels:

Rolling Error Trend

Event Volume Drift

Early Warning Indicators

⚙️ Setup & Configuration
Installation

Download and install the app

Restart Splunk if required

Open Splunk Ops Pulse from the Apps menu

Configuration

✔ No configuration files
✔ No credentials
✔ No lookups required

Simply select the index you want to monitor using the dashboard input.

📌 Data Requirements

The app works with any Splunk data that includes:

Field	Requirement
_time	Required
severity	Recommended (info, error, critical)
Raw log text	Optional

Error detection is based on:

Structured severity field (error, critical)

No dependency on _raw parsing

🧪 Test Data (Synthetic)

This app was validated using synthetic test datasets simulating:

Normal operations

Error spikes

Volume spikes

Slow degradation over time

⚠️ Test datasets are NOT packaged with the app, in compliance with Splunkbase guidelines.

Users may generate or upload their own test data to validate behavior.

🔐 Security & Compliance

No external network calls

No data export

No credentials stored

No personally identifiable information (PII)

Read-only by default for non-admin users

📄 Alerts (Optional)

The app includes disabled-by-default saved searches for:

Error spikes

Health score degradation

Admins may enable and customize alerts as needed.

🆓 Licensing & Compatibility

License: Apache 2.0

Splunk License: Free & Enterprise compatible

Dependencies: None

Python: Not required

MLTK: Not required

🖥 Supported Versions

Splunk Enterprise 8.x+

Splunk Free License

Tested on clean Splunk installations

📸 Screenshots

Screenshots of all dashboards are included in:

README/screenshots/

🧭 Roadmap (Future Enhancements)

Planned improvements may include:

Configurable health score weighting

Per-service views

Trend comparison across environments

Optional alert templates

Exportable reports

👤 Author & Support

Author: Ubaid Pisuwala
App Name: Ops Pulse
Version: 1.1.0

For feedback or enhancements, please use Splunkbase comments or your preferred issue-tracking system.