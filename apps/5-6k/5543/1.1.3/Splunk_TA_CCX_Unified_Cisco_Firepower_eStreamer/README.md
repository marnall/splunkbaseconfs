**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

CCX Security Operations has taken it upon ourselves to update and improve the existing Firepower syslog and Cisco Secure eStreamer Client (f.k.a Firepower eNcore) Add-On for Splunk as to ensure it is as CIM compliant as possible.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Cisco Firepower eStreamer and Firepower syslog.
The Technical Addon replaces the publicly available TA on Search Heads and it is based on the latest version.
Originally released here; https://splunkbase.splunk.com/app/4785/ 

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Malware, Web, Network Traffic, Network Resolution (DNS), and Intrusion Detection (IDS).

   
**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Service Provider | CyberCX |

**Requirements:**

- This Add-on is intended to be installed on Search Heads.

**Installation:**

- This Add-On is intended to be installed on Search Heads.
- Require Add-on "Cisco Secure eStreamer Client (f.k.a Firepower eNcore) Add-On for Splunk" (https://splunkbase.splunk.com/app/3662/) to be installed on Splunk Cloud IDM or Splunk Heavy Forwarder to pull data and to facilitate Firepower syslog ingestion.
- Is recommended to use separate index.

**Release Notes:**

- Enhance Firepower syslog log field extraction capturing  
- New eventtypes and tags
- Update on CIM fields
- Support datamodel Alert

**Known issues:**

- (none)


**Attribution:**

CyberCX acknowledges the excellent (foundation) work done by the Cisco team to provide this TA.