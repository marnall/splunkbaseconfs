**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for BeyondTrust Products looks to provide field extraction and CIM compliance for BeyondTrust Products log sources captured via Splunk Connect for Syslog (sc4s) or via \*HEC.

This Technical Add-on does not rely on any other Apps. Please use the links provided to configure Splunk Connect for Syslog JSON format:

https://splunk.github.io/splunk-connect-for-syslog/main/sources/vendor/BeyondTrust/sra/ (modifying main sourcetype from "beyondtrust:sra" to "ccx:beyondtrust:json")
https://www.beyondtrust.com/docs/beyondinsight-password-safe/documents/bi/integrations/bi-ps-third-party-integration.pdf (page #67 JSON format)

Currently this add-on provides extraction and CIM compliance for products:

- Privileged Remote Access (PRA)
- BeyondInsight Password Safe
- BeyondTrust Privilege Management Cloud (PAM)
- BeyondTrust Secure Remote Access

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Change, Malware Operations (FileHash), Endpoint Process, and Network Traffic.

**Compatibility:**
| Splunk Enterprise versions | 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 5.x |
| Platforms | BeyondTrust |
| Vendor Products | BeyondTrust |
| Service Provider | CyberCX |

**Requirements:**

- This Add-on is intended to be installed on Splunk Search Heads and on Splunk Forwarder where BeyondTrust logs arrives in Splunk.
- This Technical Add-on does not rely on any other Apps. Please use the links provided to configure Splunk Connect for Syslog JSON format:
  https://splunk.github.io/splunk-connect-for-syslog/main/sources/vendor/BeyondTrust/sra/ (modifying main sourcetype from "beyondtrust:sra" to "ccx:beyondtrust:json")
  https://www.beyondtrust.com/docs/beyondinsight-password-safe/documents/bi/integrations/bi-ps-third-party-integration.pdf (page #67 JSON format)

**Installation**

- This Add-on is intended to be installed on Splunk Search Heads and on Splunk Forwarder where BeyondTrust logs arrives in Splunk.

**Known issues:**

- none
