**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Unified Splunk Add-on for Checkpoint looks to provide a single field extraction bundle for all Checkpoint products.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Checkpoint ingested logs via OPSEC LEA Server or via the new SYSLOG support or Checkpoint Cloud log-push Syslog.

Below some of the listed products supported:  
- Firewall
- IPS
- Smartdefense
- Connectra
- Anti Spam (MTA)
- Endpoint Management/Compliance
- Threat Emulation
- Anti Bot
- Anti Virus
- Anti Ransomware
- Anti Virus
- Anti Malware
- Mobile
- URL Filtering
- Checkpoint Harmony (including all Products)

To receice a full list of Checkpoint products supported by this TA refer to "SUPPORT" >> "Contact Developer".

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Network Traffic, Network Sessions, Web, Authentication, Change, Malware, Endpoint, Intrusion Detection (IDS), Alerts, Email.

- Log ingestion via OPSEC LEA Server please check installation requirements on this page.

- Support available for SYSLOG ingestion via HTTP Event Collector (HEC) or via Splunk Heavy Forwarder
   
**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Checkpoint |
| Service Provider | CyberCX |

**Requirements:**

- To retrieve the logs from OPSEC LEA Server is required additional 'Splunk Add-on for Check Point OPSEC LEA' version 5.0.0 (https://splunkbase.splunk.com/app/3197/) installed on a Heavy Forwarder.

**Installation**

Log ingestion via OPSEC LEA Server:
- The CCX Unified Splunk Add-on for Checkpoint should be installed on Search Heads and Indexers.
- Splunk Add-on for Check Point OPSEC LEA version 5.0.0 (https://splunkbase.splunk.com/app/3197/) installed on a Heavy Forwarder.

SYSLOG ingestion via HTTP Event Collector (HEC)
- The CCX Unified Splunk Add-on for Checkpoint should be installed on all Search Heads and Indexers (default sourcetype cp_log).

SYSLOG ingestion via Splunk Heavy Forwarder (HF)
- The CCX Unified Splunk Add-on for Checkpoint should be installed on Search Head, Indexers and Heavy Forwarder (default sourcetype cp_log:syslog).

**Known issues:**

- none

**Release**

- New CIM field extraction coverage for Checkpoint Harmony including all sub-products.
- Enhance transforms REGEX to assist on parsing and matching sources.


