**About Us:**

CyberCX is Australia’s greatest force of cyber security. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX DUO Connector Support provide additional support for both Add-ons "Duo Splunk Connector" and "Cisco Security Cloud", and looks to enhance, improve extraction, and tagging for Duo logs.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Duo logs ingested via Duo Splunk Connector API or Cisco Security Cloud API integrations.

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, and Change.

- The CCX DUO Connector Support Add-on for "Duo Splunk Connector" (https://splunkbase.splunk.com/app/3504/) provide an additional sourcetype for selection ("duo") which replaces the use of default json by Splunk.
*Please under "More settings" on "Duo Splunk Connector" setup select Set sourcetype to "duo" and proceed.

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | DUO |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads and wherever "Duo Splunk Connector" is installed.
- Install Add-on Duo Splunk Connector (https://splunkbase.splunk.com/app/3504/) version 1.1.9 OR Add-on Cisco Security Cloud (https://splunkbase.splunk.com/app/7404) version 3.3.1 or higher.

**Installation**
- Splunk Cloud Victoria Experience
Install both Add-ons "CCX DUO Connector Support" and "Duo Splunk Connector" on the AdHoc SH.
*For Enterprise Security "ES" customers both Add-ons will be replicated across the ES and AdHoc automatically.

OR 

Install both Add-ons "CCX DUO Connector Support" and "Cisco Security Cloud" on the AdHoc SH.
*For Enterprise Security "ES" customers both Add-ons will be replicated across the ES and AdHoc automatically.

- Splunk Cloud Classic 
Install both Add-ons "CCX DUO Connector Support" and "Duo Splunk Connector" OR "Cisco Security Cloud" on the IDM.
Install only Add-on "CCX DUO Connector Support" on Search Heads.

- Splunk Enterprise (onPrem)
The Add-on "CCX DUO Connector Support" is intended to be installed on Splunk Search Heads and whenever "Duo Splunk Connector" is installed.

*To configure "Duo Splunk Connector" please under "More settings" on "Duo Splunk Connector" setup select Set sourcetype to "duo" and proceed.

**Known issues:**
- None
