# IT Ops & Security Health

## Overview
IT Ops & Security Health is a Splunk application that provides operational,
security, and data-ingestion visibility using built-in Splunk logs.

The app is designed for IT Operations, Splunk Administrators, and Security teams
to quickly understand:
- Overall platform health
- Authentication risk
- System errors and warnings
- Data coverage and ingestion quality

This app is fully compatible with Splunk Enterprise Free and does not require
any premium Splunk apps.

---

## Key Features
- Executive Health KPIs (Errors, Warnings, Login Failures, Health Score)
- Authentication Risk Analysis
- System Health Monitoring
- Data Coverage & Quality Monitoring
- Volume Trends and Baseline Deviation
- Clean navigation and drill-down–ready dashboards

---

## Dashboards Included

### 1. Home
Executive overview with high-level KPIs summarizing:
- System Errors (24h)
- System Warnings (24h)
- Failed Logins (24h)
- Overall Health Score (0–100)

---

### 2. Authentication Risk Overview
Security-focused dashboard that highlights:
- Failed login attempts
- Users affected by authentication failures
- Login failure trends
- Potential brute-force indicators

Data Source:
- index=_audit

---

### 3. System Health Overview
Operational dashboard for Splunk platform monitoring:
- Errors and warnings by component
- Error and warning trends
- Error-to-warning ratio
- Root cause indicators

Data Source:
- index=_internal
- sourcetype=splunkd

---

### 4. Data Coverage & Quality
Platform reliability dashboard that monitors:
- Data freshness
- Event volume trends
- Silent sourcetypes
- Ingestion gaps and volume drops

Data Source:
- index=*

---

## Macros Used
This app uses macros to ensure clean, reusable, and maintainable SPL.

| Macro Name | Description |
|----------|-------------|
| ops_last_24h | Standard 24-hour time window |
| ops_system_errors | Splunk system error events |
| ops_system_warnings | Splunk system warning events |
| auth_login_failures | Authentication failure events |
| all_events | All indexed events (demo usage) |

Macros are defined in:
