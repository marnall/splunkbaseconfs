
**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Extensions for Centrify (PAM) looks to provide a single field extraction bundle for Centrify (PAM) logs.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Centrify (PAM).

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Authentication, and Change.

**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Centrify (PAM) |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads as an extension to where Centrify Add-on for Splunk is installed.

To install Centrify Add-on for Splunk follow the link:
https://splunkbase.splunk.com/app/3271

**Installation**
- This Add-on is intended to be installed on Splunk Search Heads as an extension to where Centrify Add-on for Splunk is installed.

- Modify manually "Calculated Field": copy "Calculated Fields" "action", "severity_for_centrifyseverity", and "vendor_product" from CCX Extensions Add-on into the default configuration (Centrify Add-on for Splunk)

- Modify manually "Eventtype": copy the eventtype from centrify_authentication from CCX Extensions Add-on into default centrify_authentication (Centrify Add-on for Splunk)

- Modify manually "Field transformations": copy the regex from centrify_headers from CCX Extensions Add-on into default centrify_headers (Centrify Add-on for Splunk)

**Known issues:**
- none