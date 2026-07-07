**About Us:**

Enosys Solutions is a technology security specialist with a highly skilled professional services team and 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia, specialising in Security Operations services leveraging Splunk.

**Description:**

Enosys created this Technical Add-On to enable CIM-compliant ingestion of logging data from a forwarded Cylance Protect logs.

**Features:**

- This is intended to support field extraction for Splunk Cloud and Enterprise deployments.
- As this is intended for use on Search Heads no binaries are included.
- Efforts to ensure CIM compliance are met.
- The Enosys Add-on for Cylance Protect works with expected Cylance Protect type logs threat,device,indicator, audit and event.
- Additional support for syslog ingestion
   
**Compatibility:** 

| Splunk Enterprise versions |  8.1, 8.0, 7.3, 7.2, 7.1, 7.0 |
| --- | --- |
| CIM | 4.x |
| Platforms | Platform independent |
| Vendor Products | Cylance Protect |

**Requirements:**

- This Add-on requires additional 'CylancePROTECT Add-on for Splunk Enterprise ' (https://splunkbase.splunk.com/app/3709/) installed on a Heavy Forwarder to retrieve the raw logs via the CylancePROTECT API endpoint and to support syslog logs parsing.

**Installation:**
 
- The Add-on Enosys Add-on for Cylance Protect should be installed on Search Heads and Indexers.
- CylancePROTECT Add-on for Splunk Enterprise ' (https://splunkbase.splunk.com/app/3709/) installed on a Heavy Forwarder
- The eventtypes stanza 'cylance_index' should be updated to match your named index (if differs from default 'cylance_protect').


**Addressed Issues:**

- Additional CIM fields included
- Field extraction fixes  

**Attribution:**

Enosys acknowledges the efforts of TonyLeeVT for their work and maintenance of the foundation component 'https://splunkbase.splunk.com/app/3709/'
