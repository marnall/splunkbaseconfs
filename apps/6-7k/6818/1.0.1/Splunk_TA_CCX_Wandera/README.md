**About Us:**

CyberCX is the Australia’s greatest force of cyber security. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Add-on for Jamf Wandera looks to provide field extraction bundle for Jamf Wandera Threat Events Stream.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA avaliable for;
- Jamf Wandera Threat Events Stream - HTTP Event Collector (JSON)

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Inventory, Network Traffic, Intrusion Detection (IDS), Malware, and Web.

**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Service Provider | CyberCX |
| Vendor Products | Jamf Wandera |

**Requirements:**

- This Add-on is intended to be installed on Splunk Search Heads and also where HTTP Event Collector is configured.

**Installation:**

This Add-on is intended to be installed as follows:

- Splunk Cloud Victoria or Classic STACKs: Installed on Search Heads

- Splunk Enterprise: Installed on Search Heads and also where HTTP Event Collector is configured (HF)

Jamf wandera - Configuring the Threat Events Stream for Splunk via HTTP Event Collector

https://learn.jamf.com/bundle/jamf-security-documentation/page/Configuring_the_Threat_Events_Stream_with_Splunk_via_HTTP_Event_Collector.htmlInstall

- Main sourcetype to be selected as part of inputs configuration: "jamf:wandera:hec"


**Known issues:**

- (none)
 