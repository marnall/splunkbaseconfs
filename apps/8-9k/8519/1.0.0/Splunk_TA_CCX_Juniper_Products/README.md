**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Add-on for Juniper Products looks to provide a single field extraction bundle for Juniper NetScreen Firewall and Junos OS using syslog.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Juniper logs.

Below is the listed products supported:  
- Juniper Junos OS
- Juniper Netscreen Firewall

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Network Traffic, Authentication, Change, and Intrusion Detection (IDS).

- Support available for SYSLOG ingestion.

Attribution: - Full credit to the Splunk team for their work and maintenance of the foundation and components 
'https://splunkbase.splunk.com/app/2847'

**Compatibility:** 

| Splunk Enterprise versions | 10.2, 10.1, 10.0, 9.4, 9.3 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Juniper Networks |
| Service Provider | CyberCX |


**Installation**

- This Add-On is intended to be installed on Heavy Forwarders and Search Heads.
- Is recommended to use separate index.
- Use main sourcerype for ingestion: juniper
- This Add-on does not rely on any other Apps.

**Known issues:**

- none