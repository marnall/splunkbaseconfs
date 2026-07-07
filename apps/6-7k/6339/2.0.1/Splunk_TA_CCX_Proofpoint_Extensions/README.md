**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

CCX Security Operations has taken it upon ourselves to improve the existing Splunk Add-ons "Proofpoint On Demand Email Security Add On" and "Proofpoint TAP Modular Input" as to ensure it is as CIM compliant as possible.

This TA does not replace the public Splunk Add-ons for "Proofpoint On Demand Email Security Add On" and "Proofpoint TAP Modular Input", but works as an additional extension to be deployed on Search Heads (only).

Currently this add-on provides additional field extraction and CIM compliance for sourcetypes:

- pps_messagelog (Proofpoint On Demand Email Security)
- proofpoint_tap_siem (Proofpoint Targeted Attack Protection - TAP)
- ccx:proofpoint:trap:hec (Proofpoint Threat Response Auto-Pull - TRAP)


Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Email, Intrusion Detection (IDS), and Malware.

   
**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Proofpoint |
| Service Provider | CyberCX |

**Requirements:**

- This Add-on is intended to be installed on Splunk Search Heads.
- Install Add-on Proofpoint On Demand Email Security Add-on (https://splunkbase.splunk.com/app/4327/) version 2.7.0 or higher.
- Install Add-on Proofpoint TAP Modular Input (https://splunkbase.splunk.com/app/3681) version 1.4.1 or higher.

**Installation:**

- This Add-on is intended to be installed on Splunk Search Heads.
- Install Add-on Proofpoint On Demand Email Security Add-on (https://splunkbase.splunk.com/app/4327/) version 2.7.0 or higher.
- Install Add-on Proofpoint TAP Modular Input (https://splunkbase.splunk.com/app/3681) version 1.4.1 or higher.
- To configure Proofpoint Threat Response Auto-Pull (TRAP) follow the ProofPoint resource guide (https://www.proofpoint.com/au/resources/data-sheets/threat-response-auto-pull)

- After install this Extensions Add-on is recommended to "disable" the eventtype "pps_email" and its tags under field value pair.

**Attribution:**

CyberCX acknowledges the excellent (foundation) work done by Proofpoint Splunk Integrations team to provide these TAs.