Radware CWAAP Audit Log Collector for Splunk
============================================

Collects the Radware Cloud WAAP portal Activity Log (the audit / user-activity
log: logins, configuration changes, policy edits, user management) through the
Radware Cloud API (https://api.radwarecloud.app) and indexes one JSON event per
activity record, sourcetype radware:cwaap:audit.

This add-on collects the audit log only. The audit log is available through
the API only; every other CWAAP log type (WAF and Web DDoS security events,
access logs, bot events) is delivered by CWAAP Log Exporter to Amazon S3,
Azure Blob Storage or SFTP and should be brought into Splunk from there.

Configuration
-------------
1. In the Radware Cloud portal create an API key under Accounts > API Keys and
   note the Application Protection ID shown under "Account ID Details" (a UUID).
2. In Splunk open the add-on, Inputs > Create New Input, and enter a name, the
   Application Protection ID, the API key and the target index.
3. "Initial look-back (minutes)" is the history collected on the first run only
   (default 1440 = one day; 43200 = 30 days; the API serves at most 100 days).
   Later runs resume from the stored checkpoint.
4. "Maximum catch-up (minutes)" limits how far back the input catches up after
   an outage (default one day).
5. Proxy (HTTP, SOCKS4, SOCKS5, optional authentication, remote DNS) and log
   level are under Configuration.

The add-on log is $SPLUNK_HOME/var/log/splunk/ta_radware_cwaap_audit_collector_cwaap_audit.log
(search: index=_internal source=*ta_radware_cwaap_audit_collector*).

Fields
------
Events are indexed as JSON; fields such as userEmail, activityType, processTypeText,
status, userIp, userCountry, userAgent and trackingId are extracted at search
time. The field names used by the legacy "Radware CWAF Event Collector"
(Splunkbase 5281) - user, id, details, activity, status, userIP, country,
user_agent, event_type - are provided as search-time aliases so existing
searches and dashboards keep working.

Migration
---------
From the legacy Radware CWAF Event Collector (Splunkbase 5281, old portal):
create an input here with an initial look-back that covers the period since
the legacy collector last ran, then disable the legacy "user_activity" input.

From the Radware CWAAP Event Collector (Splunkbase 7857) audit log type:
create an input here, then disable or delete the audit input in that add-on,
otherwise the same records are indexed twice. Both add-ons use the same
sourcetype and field names; no search changes are needed.

Where to install
----------------
Single instance: on that instance. Distributed Splunk Enterprise: on the heavy
forwarder (or inputs data manager) that runs modular inputs, and on the search
heads so the sourcetype settings and field aliases apply at search time;
indexers do not need it. Splunk Cloud Platform: install from the app browser
and create the input there, or run the input on a customer-managed heavy
forwarder that sends to the stack. Requires Splunk 9.3 or later (Python 3.9)
and outbound HTTPS to api.radwarecloud.app, directly or through the configured
proxy.

Release notes
-------------
1.0.0
- Initial release: audit (portal user-activity) log collection through the
  Radware Cloud API. Duplicate-safe checkpoints (newest event time plus the
  ids seen at that time), one-day catch-up slices, retry with back-off on
  HTTP 429 and 5xx, a run stops at the first failed request so no slice is
  skipped, clear logging of authentication errors (401/403) and of the API's
  100-day history limit. Proxy with type, authentication and remote DNS
  resolution. Built on the Splunk UCC framework; Splunk Cloud compatible.

Support
-------
This add-on is provided as-is and is not covered by Radware support contracts.
Questions and issues: support@radware.com
