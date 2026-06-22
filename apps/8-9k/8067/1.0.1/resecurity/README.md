Resecurity TAXII 2.x IOC Input for Splunk
=========================================

This app adds a modular input that collects Indicators of Compromise (IOCs) from a TAXII 2.x server and indexes them into Splunk.

What you can do with it
- Collect IOCs from a TAXII 2.x collection on a schedule
- Control how far back to fetch on the first run
- Search and analyze IOCs in Splunk with simple SPL

Quick start
1) Open the app and complete Setup
- Go to Apps → Resecurity (the app’s landing page).
- Fill in global settings:
  - Base URL (e.g., https://example.com/taxii2)
  - API Root
  - Verify SSL: keep enabled in production
  - Username and Password (stored securely)
- Click Save.

2) Create a data input
- Go to Settings → Data inputs → taxii2_ioc → New.
- Fill in:
  - Name: any unique name (e.g., domains)
  - Collection: TAXII 2.x collection ID or name
  - Initial lookback (optional): e.g., 24h, 7d (default 24h)
  - Limit (optional): page size (e.g., 200–1000)
  - Interval: choose your polling interval, we recommend use 3600 seconds (1 hour)
- Save the input.

3) Verify data in Search
- Open Search & Reporting and try:
```
sourcetype="taxii2_ioc" | table _time indicator indicator_type stix_type stix_id labels confidence description | sort - _time
```
Common searches
- Most recent per IOC:
```
sourcetype="taxii2_ioc" | stats latest(_time) as last_seen values(stix_type) as stix_type values(labels) as labels values(confidence) as confidence values(description) as description by indicator indicator_type | convert ctime(last_seen) | sort - last_seen
```
- Top indicator types:
```
sourcetype="taxii2_ioc" | stats count by indicator_type | sort - count
```

How to configure inputs well
- Initial lookback controls how far back the first run can go and serves as a “floor” for further runs.
- Interval defines how often Splunk will call the input (e.g., every 5 minutes).
- Use a dedicated index (optional) to keep IOCs separate from other data.
- Suggested sourcetype: taxii2_ioc.

Where to look if something is wrong
1) No data in Search
- Make sure the input is enabled (Settings → Data inputs → taxii2_ioc).
- Broaden the time range (e.g., All time) and search only by sourcetype:
```
sourcetype="taxii2_ioc"
```
- If you set a custom index, include it in your search (index=<your_index>).

2) Check app logs
- Internal logs show requests and progress:
```
index=_internal ("modular input" OR ExecProcessor OR taxii2_ioc OR resecurity)
```
- Look for messages like:
  - request: url=... added_after=...
  - checkpoint update: old=... → new=...
  - done, events=N

3) Verify the final configuration loaded by Splunk
   - From the Splunk server shell:
```
splunk btool inputs list --app=resecurity --debug | sed -n '/taxii2_ioc/,+20p'
```

4) Setup issues
- Ensure API Root, Username, and Token are provided on the setup page.
- If SSL verification fails in a test environment, temporarily disable Verify SSL in global settings (not recommended for production).

Tips
- Start with a moderate interval (e.g., 300 seconds) and adjust later.
- Use Initial lookback that matches your use case (e.g., 24h or 7d).
- If you create several inputs for different collections, use meaningful names and the same sourcetype to simplify searches.

Uninstalling
- Disable your inputs (Settings → Data inputs → taxii2_ioc).
- Remove the app via Splunk UI (Manage Apps).
- Optionally delete leftover data in your target index (if dedicated).

Support
- Contact your Resecurity administrator for credentials and endpoint details.
- For operational issues, attach relevant lines from index=_internal when opening a support ticket.

Version
- 1.0.0 — initial release
