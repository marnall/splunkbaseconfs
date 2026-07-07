**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Nozomi Networks looks to provide additional field extraction and CIM compliance for Nozomi Networks log sources captured via the Add-on Nozomi Networks Sensor Add-on.

This Technical Add-on does not replace the public Splunk Add-on for Nozomi Networks Sensor Add-on (https://splunkbase.splunk.com/app/5316) but works as an additonal extension to be deployed on Search Heads (only).

Currently this add-on provides additional extraction and CIM compliance support for the following sourcetypes:  

- nozomi:captured_urls
- nozomi:link
- nozomi:session
- nozomi:link_events
- nozomi:node
- nozomi:alert
- nozomi:variable
- nozomi:nn_asset
- nozomi:health

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Intrusion Detection (IDS), Malware, Network Traffic, Network Session, Inventory, Endpoint, Performance, and Web.

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Nozomi Netwroks |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed following the installation guidance.
- Install Add-on Nozomi Networks Sensor Add-on (https://splunkbase.splunk.com/app/5316) version 1.3.2 or higher

**Installation**
This Add-on is intended to be installed as follows:
- Splunk Cloud Victoria STACKs: Installed on Search Head
- Splunk Cloud Classic STACKs: Installed on Search Heads
- Splunk Enterprise: Installed on Search Heads

This Add-on is intended to be installed as a companion for the following add-on:
- Install Add-on Nozomi Networks Sensor Add-on (https://splunkbase.splunk.com/app/5316) version 1.3.2 or higher
 

**Known issues:**
- Modify manually "Eventtype": disable eventtype "nozomi_all_alerts" and tags for "nozomi_all_alerts"
- Modify manually "Calculated Field" (nozomi:alert): copy "Calculated Fields" search "signature", "protocol", and "severity" from CCX Add-on for Nozomi Networks Extension into the default configuration
- Modify manually "Calculated Field" (nozomi:node): copy "Calculated Fields" search "vendor_product" from CCX Add-on for Nozomi Networks Extension into the default configuration
- Modify manually "Calculated Field" (nozomi:nn_asset): copy "Calculated Fields" search "vendor_product", and "os" from CCX Add-on for Nozomi Networks Extension into the default configuration
- Modify manually "Eventtype": remove tags "performance" and "os" from eventtype "nozomi_all_nn_assets"

**Addressed Issues:**
- Fix issues detected on sourcetype "nozomi:alert" with fields "type" and "severity" not outputing expected values.
