**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Sophos XG Firewall looks to provide additional field extraction and CIM compliance for Sophos Next Generation Firewall log sources captured via Syslog.

This Technical Add-on does not replace the public Splunk Add-on Sophos Next-Gen Firewall (https://splunkbase.splunk.com/app/6187) but works as an additonal extension to be deployed on Search Heads (only).

Currently this add-on provides additional extraction and CIM compliance for the follow sourcetypes:

- sophos:xg:content_filtering  
- sophos:xg:firewal
- sophos:xg:event
- sophos:xg:sandbox
- sophos:xg:anti_spam

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Authentication, Email, Network Traffic, Network Session, Performance and Web.

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Sophos XG Firewall |
| Service Provider | CyberCX |

**Requirements:**
- Install CCX Add-on for Sophos XG Firewall on Search Heads only.
- Install Splunk Add-on Sophos Next-Gen Firewall (https://splunkbase.splunk.com/app/6187) version 1.0.1 or higher


**Installation:**
- Install CCX Add-on for Sophos XG Firewall on Search Heads only.

This Add-on is intended to be installed as a companion for the following add-ons:
- Install Splunk Add-on Sophos Next-Gen Firewall (https://splunkbase.splunk.com/app/6187) version 1.0.1 or higher


**Known issues:**
Manual fixes to be performed from CCX Add-on for Sophos XG Firewall configuration to Sophos Next-Gen Firewall - sourcetype: "sophos:xg:content_filtering"
- Modify manually "Field Alias": FIELDALIAS-sophos_xg_content_filtering_category to FIELDALIAS-sophos_xg_content_filtering_category - http_category AS http_category
- Modify manually "Calculated Field": copy "Calculated Fields" search for "src", "dest", and "dest_port" to the default configuration of the Add-on Sophos Next-Gen Firewall (overwrite default)

Manual fixes to be performed from CCX Add-on for Sophos XG Firewall configuration to Sophos Next-Gen Firewall - sourcetype: "sophos:xg:event"
- Modify manually "Calculated Field": copy "Calculated Fields" search for "action", "user", and "dest" to the default configuration of the Add-on Sophos Next-Gen Firewall (overwrite default)
- Modify manually "Event types": copy eventtype "sophosxg_authentication" search string from CCX Add-on for Sophos XG Firewall into default eventtype "sophosxg_authentication" on Sophos Next-Gen Firewall 
