# Testing - splunk_app_vercel

Date executed: 2026-01-28

## Test cases

### 1) Macros scope
- Purpose: confirm default macro scopes to index=vercel.
- Check: default/macros.conf -> vercel_index definition.
- Expected: `vercel_index` expands to index=vercel.

### 2) Core Web Vitals dashboard
- Purpose: confirm panels render against vercel:speed_insights.
- Expected search (example):
  - `vercel_speed_insights` | stats perc75(lcp)
- Expected: panels show values when Speed Insights data exists.

### 3) Deployment Health dashboard
- Purpose: validate error panels against vercel:logs.
- Expected search (example):
  - `vercel_index` sourcetype=vercel:logs status>=500 | timechart count
- Expected: panels render and table populates when logs data exists.

### 4) Edge Security dashboard
- Purpose: validate traffic/anomaly panels for Web data.
- Expected search (example):
  - `vercel_web` | stats count by src_ip
- Expected: panels render and map populates when geo data exists.

### 5) Alerts (disabled by default)
- Purpose: confirm saved searches are valid and schedulable.
- Action: enable in Splunk UI and adjust thresholds to data volume.
- Expected: search returns results when conditions are met.

## Tests executed
- AppInspect (precert): PASS with OS-related warnings only
  - Report: E:\Splunk Addon\appinspect_reports\splunk_app_vercel_appinspect.json
