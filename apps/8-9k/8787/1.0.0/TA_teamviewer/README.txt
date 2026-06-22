TeamViewer Add-on for Splunk
============================

Collects and parses TeamViewer log files from Windows endpoints into Splunk.

LOG SOURCES
-----------
- TeamViewer15_Logfile.log  (sourcetype: teamviewer)
- TVNetwork.log             (sourcetype: teamviewer:network)
- TeamViewer15_Hooks.log    (sourcetype: teamviewer)

Default log path: C:\Program Files\TeamViewer\
Default index:    teamviewer

REQUIREMENTS
------------
- Splunk Enterprise / Universal Forwarder 8.2+
- TeamViewer 15.x on Windows
- Python 3.7 - 3.13

CIM DATA MODELS
---------------
- Authentication
- Network Sessions
- Network Traffic
- Data Access

RELEASE NOTES
-------------
v1.0.0 (2026-05-28)
  New
  - File monitor inputs for TeamViewer15_Logfile.log, TVNetwork.log,
    and TeamViewer15_Hooks.log
  - CIM-compliant field extractions for sourcetypes teamviewer and
    teamviewer:network covering Authentication, Network Sessions,
    Network Traffic, and Data Access data models
  - 12 event types mapped to CIM tags
  - 5 pre-built alerts: new outgoing session, file transfer detected,
    authentication failure, session from unknown IP, service restart
  - 3 scheduled reports: daily session summary, top remote partners,
    file transfer report
  - Lookup table (teamviewer_codes.csv) for log code prefix descriptions

  Fixed
  - All saved searches include dispatch.earliest_time for Splunk Cloud
    compatibility
  - CIM action field values corrected (removed invalid "attempt" value;
    added "read"/"write" for Data Access events)
  - transport field normalised to lowercase (tcp/udp) per CIM spec
  - direction field corrected to inbound/outbound per CIM Network Traffic
    spec
  - user_type corrected to "user" per CIM Authentication spec

For full documentation see README.md in the source repository.
