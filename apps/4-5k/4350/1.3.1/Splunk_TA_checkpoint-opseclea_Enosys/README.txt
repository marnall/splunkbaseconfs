**About Us:**

Enosys Solutions is a technology security specialist with a highly skilled professional services team and 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia, specialising in Security Operations services leveraging Splunk.

**Description:**

Enosys created this Technical Add-On to enable CIM-compliant ingestion of logging data from a forwarded Check Point logs.

**Features:**

- This is intended to support field extraction for Splunk Cloud and Enterprise deployments.
- As this is intended for use on Search Heads no binaries are included.
- Efforts to ensure CIM compliance are met.
- The Enosys Add-on for Check Point OPSEC LEA works with expected Check Point type logs opsec,opsec:smartdefense(ips),opsec:vpn,opsec:audit,opsec:threat_emulation,opsec:anti_malware(anti_bot) and opsec:anti_virus
   
**Compatibility:** 

| Splunk Enterprise versions |  7.3, 7.2, 7.1, 7.0 |
| --- | --- |
| CIM | 4.10, 4.11, 4.12, 4.13 |
| Platforms | Platform independent |
| Vendor Products | CheckPoint |

**Requirements:**

- This Add-on requires additional 'Splunk Add-on for Check Point OPSEC LEA' version 4.3.1 (https://splunkbase.splunk.com/app/3197/) installed on a Heavy Forwarder to retrieve the logs from OPSEC LEA Server.

**Installation:**

- The Add-on Enosys Add-on for Check Point OPSEC LEA should be installed on Search Heads and Indexers.
- Splunk Add-on for Check Point OPSEC LEA version 4.3.1 (https://splunkbase.splunk.com/app/3197/) installed on a Heavy Forwarder

**Known issues:**

- (none)
