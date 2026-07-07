**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Cloudflare Products looks to provide field extraction and CIM compliance for Cloudflare log sources captured via HTTP Event Collector Logpush to Splunk.

This Technical Add-on does not rely on any other Apps. Please use the link provided to Enable Logpush to Splunk via the Cloudflare dashboard:

https://developers.cloudflare.com/logs/get-started/enable-destinations/splunk/

Currently this add-on provides extraction and CIM compliance for sourcetypes:  

- ccx:cloudflare:zerotrust:network_sessions (Zero Trust Network Session)
- ccx:cloudflare:gateway_network (Gateway Network)
- ccx:cloudflare:access_requests (Access requests)
- ccx:cloudflare:gateway_dns (Gateway DNS)
- ccx:cloudflare:audit_logs (Audit logs)
- ccx:cloudflare:gateway_http (Gateway HTTP)
- ccx:cloudflare:waf (WAF)

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Authentication, Change, Intrusion Detection (IDS), Malware, Network Traffic, and Web.

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Cloudflare |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads and on Splunk Forwarder where HEC for Cloudflare is configured.
- This Technical Add-on does not rely on any other Apps. Please use the link provided to Enable Logpush to Splunk via the Cloudflare dashboard:
https://developers.cloudflare.com/logs/get-started/enable-destinations/splunk/

**Installation**
- This Add-on is intended to be installed on Splunk Search Heads and on Splunk Forwarder where HEC for Cloudflare is configured.
- This Technical Add-on does not rely on any other Apps. Please use the link provided to Enable Logpush to Splunk via the Cloudflare dashboard:
https://developers.cloudflare.com/logs/get-started/enable-destinations/splunk/
- Main sourcetype to be used for log parsing is: cloudflare:json (logs will be automatically assinged to expected sourcetypes)

**Known issues:**
- none

