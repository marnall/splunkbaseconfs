**About Us:**
CyberCX is Australia's greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Zscaler Products Extensions looks to provide a single field extraction bundle for Zscaler logs.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Zscaler.

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

CCX Zscaler Products Extensions currently supports the following products:

- Zscaler_ZPA
- Zscaler_ZIA_Firewall
- Zscaler_ZIA_Proxy

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Authentication, DLP, IDS, Malware, Network Session, Network Traffic, and Web.

CCX Zscaler Products Extensions provides additional CIM field coverage and tagging to the following sourcetypes:

- zscalerlss-zpa-app
- zscalerlss-zpa-auth
- zscalerlss-zpa-connector
- zscalernss-fw
- zscalernss-web

**Compatibility:**

| Splunk Enterprise versions | 10,9.4,9.3,9.2,9.1   |
| -------------------------- | -------------------- |
| CIM                        | 6.x, 5.x             |
| Platforms                  | Platform independent |
| Vendor Products            | Zscaler              |
| Service Provider           | CyberCX              |

**Requirements:**

- This Add-on is intended to be installed on Splunk Search Heads as an extension to where Zscaler Technical Add-On for Splunk is installed.

**Installation**

- This Add-on is intended to be installed on Splunk Search Heads as an extension to where Zscaler Technical Add-On for Splunk is installed.
- Zscaler link: https://splunkbase.splunk.com/app/3865

Fields to be replaced from Zscaler Technical Add-On for Splunk with CCX Zscaler Products Extensions fields:

- Calculated fields:
- - zscalernss-web: EVAL-dlp_type
- - zscalernss-fw: EVAL-action
- - EVAL-vendor_product for all sourcetypes

- Event types:
- - Zscaler_Proxy_General

- Tags:
- - eventtype=Zscaler_Proxy_General (disable: communicate, end, network, session, start)

**Known issues:**

- none
