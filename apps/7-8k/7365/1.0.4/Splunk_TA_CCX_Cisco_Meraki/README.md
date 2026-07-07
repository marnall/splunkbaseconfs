**About Us:**
CyberCX is Australia's greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Cisco Meraki looks to provide a single field extraction bundle for Cisco Meraki logs.

This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Cisco Meraki.

Currently this add-on provides additional field extraction and CIM compliance for the following sourcetypes:

- ccx:meraki:sc4s
- ccx:meraki:sc4s:events
- ccx:meraki:sc4s:firewall
- ccx:meraki:sc4s:flows
- ccx:meraki:sc4s:urls

- meraki:accesspoints
- meraki:audit
- meraki:cameras
- meraki:organizationsecurity
- meraki:securityappliances
- meraki:switches

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Change, IDS, Malware, Network Traffic, Network Sessions, and Web.

**Compatibility:**

| Splunk Enterprise versions | 9.2, 9.1, 9.0, 8.2   |
| -------------------------- | -------------------- |
| CIM                        | 4.x 5.x              |
| Platforms                  | Platform independent |
| Vendor Products            | Cisco Meraki         |
| Service Provider           | CyberCX              |

**Requirements:**

- This Add-on is intended to be installed on Splunk search heads where Splunk TA for Cisco Meraki is installed.

**Installation:**

- This Add-on is intended to be installed on Splunk search heads where Splunk TA for Cisco Meraki is installed.

- This TA requires the following config to be overwritten from CCX Add-on for Cisco Meraki to where Splunk TA for Cisco Meraki is installed.

Calculated Fields:

- meraki:accesspoints:
- - EVAL-app
- - EVAL-description
- - EVAL-dest
- - EVAL-dvc
- - EVAL-src
- - EVAL-src_ip
- - EVAL-src_mac
- - EVAL-type
- - EVAL-vendor_product
- meraki:audit
- - EVA-action
- - EVA-status
- - EVA-user
- meraki:cameras
- - EVAL-action
- - EVAL-vendor_product
- meraki:organizationsecurity
- - EVAL-action
- - EVAL-category
- - EVAL-dest
- - EVAL-dest_ip
- - EVAL-file_hash
- - EVAL-file_name
- - EVAL-file_path
- - EVAL-signature
- - EVAL-signature_id
- - EVAL-src
- - EVAL-src_ip
- - EVAL-user
- meraki:securityappliances
- - EVAL-action
- - EVAL-app
- - EVAL-description
- - EVAL-dest
- - EVAL-dest_ip
- - EVAL-dvc
- - EVAL-signature
- - EVAL-signature_id
- - EVAL-src
- - EVAL-src_ip
- - EVAL-type
- - EVAL-vendor_product

- - LOOKUP-cisco_meraki_securityappliances_action_lookup.csv
- meraki:switches
- - EVAL-action
- - EVAL-result
- - EVAL-src
- - EVAL-vendor_product

Event Types:

- meraki_api_accesspoints_alerts
- meraki_api_accesspoints_change
- meraki_api_organizationsecurity (disable tags)
- meraki_api_securityappliances_alerts
- meraki_api_securityappliances_network_sesssion

**Known issues:**

- none
