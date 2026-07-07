**About Us:**
CyberCX is Australia's greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for PureStorage Products looks to provide a single field extraction bundle for PureStorage Products.

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Authentication, and Change.

- This TA currently supports the following sourcetypes:
- - purestorage:flasharray:alerts
- - purestorage:flasharray:audit
- - purestorage:flasharray:login

**Compatibility:**

| Splunk Enterprise versions | 10,9.4,9.3,9.2,9.1   |
| -------------------------- | -------------------- |
| CIM                        | 6.x, 5.x             |
| Platforms                  | Platform independent |
| Vendor Products            | PureStorage          |
| Service Provider           | CyberCX              |

**Requirements:**

- This Add-on is to be installed on Splunk Search Heads to facilitate field extractions and CIM compliance.

**Installation:**

- This Add-on is to be installed on Splunk Search Heads to facilitate field extractions and CIM compliance.

**Known issues:**

- CCX Add-on for PureStorage Products in some cases can fail to capture/extract the event time and needs an update on TIME_PREFIX. Please follow our code details on props.conf.
