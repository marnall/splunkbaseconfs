**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Extensions for Illumio looks to provide a single field extraction bundle for Illumio logs.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Illumio.

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Authentication, and Change.

**Compatibility:**

| Splunk Enterprise versions | 10,9.4,9.3,9.2,9.1   |
| -------------------------- | -------------------- |
| CIM                        | 6.x, 5.x             |
| Platforms                  | Platform independent |
| Vendor Products            | Illumio              |
| Service Provider           | CyberCX              |

**Requirements:**

- This add-on is intended to be installed on Splunk Search Heads as an extension to Illumio Technology Add-On for Splunk.

To install Illumio Technology Add-On for Splunk for Splunk follow the link:
https://splunkbase.splunk.com/app/3657

**Installation**

- This add-on is intended to be installed on Splunk Search Heads as an extension to Illumio Technology Add-On for Splunk.

- This TA requires changes to the original TA Illumio Technology Add-On for Splunk:

- illumio:pce
- - Calculated fields: action, vendor_product
- - Event Types: ccx_illumio_pce_authentication -> illumio_authentication_events

- illumio:pce:collector
- - Calculated fields: action

**Known issues:**

- none
