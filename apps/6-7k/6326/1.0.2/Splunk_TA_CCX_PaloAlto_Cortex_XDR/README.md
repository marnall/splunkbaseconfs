**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Palo Alto Cortex XDR looks to provide a single field extraction bundle for Palo Alto Cortex XDR Syslog (CEF).
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Palo Alto Cortex XDR ingested logs from Cortex Data Lake to a Syslog Server.

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Network Traffic, Change, Malware, Alerts, and Intrusion Detection (IDS).

- Log ingestion from Cortex Data Lake to a Syslog Server requirements on Palo Alto TECHDOCS link below:
https://docs.paloaltonetworks.com/cortex/cortex-data-lake/cortex-data-lake-getting-started/get-started-with-log-forwarding-app/forward-logs-from-logging-service-to-syslog-server
   
**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Palo Alto Cortex XDR |
| Service Provider | CyberCX |

**Requirements:**

- Log ingestion from Cortex Data Lake to a Syslog Server requirements on Palo Alto TECHDOCS link below:
https://docs.paloaltonetworks.com/cortex/cortex-data-lake/cortex-data-lake-getting-started/get-started-with-log-forwarding-app/forward-logs-from-logging-service-to-syslog-server

**Installation**

SYSLOG (CEF) ingestion via HTTP Event Collector (HEC):
- The CCX Palo Alto Cortex XDR Add-on should be installed on Search Heads (default sourcetype - pan:cortexxdr:cef).

SYSLOG (CEF) ingestion via Splunk Heavy Forwarder (HF):
- - The CCX Palo Alto Cortex XDR Add-on should be installed on Search Heads and Heavy Forwaders (default sourcetype - pan:cortexxdr:cef).

**Known issues:**

- (none)
