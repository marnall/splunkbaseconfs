**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
CCX Security Operations has taken it upon ourselves to update and improve the existing Mimecast for Splunk Add-on to ensure it is as CIM compliant as possible.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Mimecast.
The Technical Addon is to be used as an extension of the publicly available TAs on Search Heads and is based on the latest version.


**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Email, Authentication, Change, Malware, Data Loss Prevention (DLP) and Intrusion Detection (IDS).

   
**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2  |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Mimecast ETP |
| Service Provider | CyberCX |

**Requirements:**
- To retrieve Mimecast logs is required additional Add-on 'Mimecast for Splunk' version 5.3.0 or higher (https://splunkbase.splunk.com/app/4075/) installed on a Heavy Forwarder or Search Head.
- This Add-on is intended to be installed on Search Heads and Indexers.

**Installation:**
- To retrieve Mimecast logs is required additional Add-on 'Mimecast for Splunk' version 5.3.0 or higher (https://splunkbase.splunk.com/app/4075/) installed on a Heavy Forwarder or Search Head.
- This Add-on is intended to be installed on Search Heads and Indexers.

**Addressed Issues:**
- New evaluated field action for 'mimecast_ttp_impersonation_protect' (mimecastttpipst) matching the Intrusion Detection (IDS) prescribed values.

**Attribution:**
CyberCX acknowledges the foundation work done by the Mimecast Services team to provide this TA.