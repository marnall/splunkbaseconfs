**About Us:**

Enosys Solutions is a technology security specialist with a highly skilled professional services team and 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia, specialising in Security Operations services leveraging Splunk.

**Description:**

Enosys created this Technical Add-On to enable CIM-compliant ingestion of logging data from a syslog forwarded ContentKeeper and ContentKeeperweb Proxy logs.

**Features:**

- This is intended to support field extraction for Splunk Cloud and Enterprise deployments.
- As this is intended for use on Search Heads no binaries are included.
- Efforts to ensure CIM compliance are met.

**Compatibility:** 

| Splunk Enterprise versions |  8.0, 7.3, 7.2, 7.1, 7.0 |
| --- | --- |
| CIM | 4.10, 4.11, 4.12, 4.13 |
| Platforms | Platform independent |
| Vendor Products | ContentKeeper Proxy |

**Requirements:**

- This Add-on requires to be installed on a Heavy Forwarder to facilitate parsing of ContentKeeper and ContentKeeperweb syslog logs ingested.

**Installation:**

- The Add-on Enosys Add-on for ContentKeeper and ContentKeeperweb Proxy should be installed on Heavy Forwarders, Search Heads and Indexers.

**Known issues:**

- (none)

**Addressed Issues:**

- New ContentKeeperweb REGEX extraction fixing capturing groups
- Sanitised URL removing ports
- Mapped eventtypes per sourcetype (contentkeeper and contentkeeper:web) 
