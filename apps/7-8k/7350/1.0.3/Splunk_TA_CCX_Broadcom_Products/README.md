**About Us:**
CyberCX is Australia's greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Broadcom Products looks to provide a single field extraction bundle for Broadcom Products logs.

This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Broadcom Products.

Currently this add-on provides additional field extraction and CIM compliance for sourcetype:

- ca:pam:syslog (Broadcom Symantec Privileged Access Management (PAM)) Syslog forwarding in XML format

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Authentication, and Change.

**Compatibility:**

| Splunk Enterprise versions | 10,9.4,9.3,9.2,9.1    |
| -------------------------- | --------------------- |
| CIM                        | 6.x, 5.x              |
| Platforms                  | Platform independent  |
| Vendor Products            | Broadcom Symantec PAM |
| Service Provider           | CyberCX               |

**Requirements:**

- This TA should be installed on Splunk Search Heads and where logs are configured to arrive in Splunk.(HF/IDM/IDXs)
- This TA supports and parses Broadcom PAM Syslog logs forwarded in XML format.

**Installation:**

- This TA should be installed on Splunk Search Heads and where logs are configured to arrive in Splunk. (HF/IDM/IDXs)

- https://techdocs.broadcom.com/content/dam/broadcom/techdocs/us/en/pdf/symantec-security-software/identity-security-pam/ca-privileged-access-manager-new-source/pam-consolidated-(jan24)/symantec-privileged-access-manager-4.1.pdf

- https://techdocs.broadcom.com/us/en/symantec-security-software/identity-security/privileged-access-manager/3-4-6/reference/messages-and-log-formats/syslog-message-formats.html

**Known issues:**

- none
