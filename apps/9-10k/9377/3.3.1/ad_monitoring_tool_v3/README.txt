Active Directory Monitoring App
===============================

Dashboards for Active Directory health, replication, authentication, audit trail,
security operations, endpoint posture, DC performance, network/process activity,
and Windows Defender.

Requirements
------------
- Splunk Enterprise 9.2+ / Splunk Cloud (Dashboard Studio with tabs)
- Windows/AD data collected with Splunk Add-on for Microsoft Windows
  (Splunk_TA_windows) from the domain controllers, including:
  - AD health monitoring inputs (MSAD:NT6:Health)
  - AD replication monitoring (MSAD:NT6:Replication) and/or NTDS
    performance counters (PerfmonMk:NTDS)
  - Windows event logs (XML or classic rendering both supported)

A host appears in the app only if it sent MSAD:NT6:Health AND at least one
DC-only signal (MSAD:NT6:Replication or PerfmonMk:NTDS) in the last 24 hours.

Configuration
-------------
- The events index is set in one place: the `ad_index` macro
  (Settings > Advanced search > Search macros). Default: index=windows-servers
- DC detection is centralized in the `ad_hosts` and `ad_hosts_list` macros.

No scripted inputs, no indexed data, no external network calls.
