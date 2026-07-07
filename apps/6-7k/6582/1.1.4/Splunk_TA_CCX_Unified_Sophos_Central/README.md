**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Unified Splunk Add-on for Sophos Central looks to provide a single field extraction bundle for Sophos Central logs.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Sophos Central ingested logs via Sophos connector script on Splunk Heavy Forwarders or via Splunk Add-on Sophos Central API.

Below some of the listed products supported:  

- Sophos Central (payload JSON)

- Sophos Central API: Alerts, Events, Tenants, and Endpoints


Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Web, Change, Malware, Intrusion Detection (IDS), Data Loss Prevention (DLP), Inventory, Enpoint.

   
**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Sophos Central |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads and Heavy Forwarders/IDM.
- Splunk Heavy Forwarder with configured Sophos-Central-SIEM-Integration solution to facilitate Sophos Central logs capturing (https://github.com/sophos/Sophos-Central-SIEM-Integration/blob/master/config.ini) or Splunk Add-on Sophos Central (API) (https://splunkbase.splunk.com/app/6186/)
- Installed on SH "Splunk Common Information Model (CIM)" (https://splunkbase.splunk.com/app/1621/)

**Installation**
- This Add-on is intended to be installed on Splunk Search Heads and Heavy Forwarders/IDM where the Sophos Central logs inputs is configured.
- The CCX Unified Add-On for Sophos Central works as an extension and support for Splunk Add-on Sophos Central (API). 


**Known issues:**
- none

