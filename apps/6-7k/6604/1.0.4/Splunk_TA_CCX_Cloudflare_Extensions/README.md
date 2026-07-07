**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Cloudflare Extensions looks to provide additional field extraction and CIM compliance for Cloudflare log sources captured via the App Cloudflare App for Splunk.

This Technical Add-on does not replace the public Cloudflare App for Cloudflare App for Splunk (https://splunkbase.splunk.com/app/4501) but works as an additonal extension to be deployed on Search Heads (only).

Currently this add-on provides additional extraction and CIM compliance for sourcetypes:  

- cloudflare:json


Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Web and Intrusion Detection (IDS).

   
**Compatibility:** 
| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Cloudflare |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads.
- Install App Cloudflare App for Splunk (https://splunkbase.splunk.com/app/4501) version 2.2.0 or higher

**Installation**
- This Add-on is intended to be installed on Splunk Search Heads.
- Install App Cloudflare App for Splunk (https://splunkbase.splunk.com/app/4501) version 2.2.0 or higher

Post steps installation to be performed:
- Update the default App sourcetype "cloudflare:json" field: src

**Known issues:**
- Copy and paste the following calculated fields over the default fields saved on Cloudflare App:
dest = if('OriginIP'=="", null(), 'OriginIP')
src = if(match('ClientIP', "((?:\d{1,3}\.){3}\d{1,3})"), 'ClientIP', null())
url = replace('ClientRequestHost', "([^\:]+)\:.+", "\1") + if('ClientRequestURI'=="/", "", 'ClientRequestURI')


