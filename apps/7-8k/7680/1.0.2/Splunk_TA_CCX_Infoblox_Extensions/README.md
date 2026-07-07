**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

CCX Security Operations has taken it upon ourselves to improve the existing Splunk Add-on "Splunk Add-on for Infoblox" as to ensure it is as CIM compliant as possible.

This TA does not replace the public Splunk Add-ons for "Splunk Add-on for Infoblox", but works as an additional extension to be deployed on Search Heads (only).

Currently this add-on provides additional field extraction and CIM compliance for sourcetypes:

- infoblox:audit
- infoblox:dns
- infoblox:threatprotect

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Change, and Intrusion Detection (IDS).

**Compatibility:**

| Splunk Enterprise versions | 10,9.4,9.3,9.2,9.1   |
| -------------------------- | -------------------- |
| CIM                        | 6.x, 5.x             |
| Platforms                  | Platform independent |
| Vendor Products            | Infoblox             |
| Service Provider           | CyberCX              |

**Requirements:**

- This Add-on is intended to be installed on Splunk Search Heads.
- Install Splunk Add-on for Infoblox (https://splunkbase.splunk.com/app/2934/)

**Installation:**

- This Add-on is intended to be installed on Splunk Search Heads.
- Install Splunk Add-on for Infoblox (https://splunkbase.splunk.com/app/2934/)

Overwrite the following Calculated Fields from this TA to Splunk Add-on for Infoblox across the following sourcetypes:

- infoblox:audit - app, change_type, src, src_ip
- infoblox:dns - dest, dest_ip, src, type

**Known issues:**

- none
