# DentiSystems Add-on for Splunk (TA-dentisystems)

## Overview
The **DentiSystems Add-on for Splunk** provides enterprise data ingestion, field normalization, and Common Information Model (CIM) compliance for active deception events, honeypot breaches, and threat intelligence captured by the DentiSystems platform (DentiGrid, GATE, LEAKS).

## Key Features
- **CIM Compliance:** Normalizes threat telemetry to the *Intrusion Detection*, *Alerts*, and *Network Traffic* CIM data models.
- **Dual Ingestion Modes:**
  1. **HTTP Event Collector (HEC):** Real-time push from DentiGrid/GATE directly into Splunk.
  2. **Modular Input:** Scheduled polling of the DentiGrid threat intelligence feed (`/api/attacks/recent`).
- **Prebuilt Operational Dashboards:** Real-time visibility into adversary IPs, attack vectors, targeted ports, and honeypot interactions.

## Installation & Setup
1. Deploy `TA-dentisystems.spl` via **Manage Apps > Install app from file** in Splunk Enterprise / Cloud.
2. Enable HTTP Event Collector (HEC) and create a token with sourcetype `dentisystems:threat`.
3. Configure the HEC endpoint in your DentiGrid admin console under **Integrations > SIEM & SOAR Pipelines**.
4. (Optional) Configure the modular input in **Settings > Data Inputs > DentiSystems Intelligence Feed**.

## License
Apache License 2.0. Copyright (c) 2026 DentiSystems Inc.
