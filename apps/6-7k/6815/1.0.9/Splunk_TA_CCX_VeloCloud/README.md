**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

Below are some of the listed products supported:
- VMWare VeloCloud SD-WAN
- - This product relies on public Splunk Add-on "VCO Events to Splunk from VMware SD-WAN" (https://splunkbase.splunk.com/app/6252/) to establish API connection call to VeloCloud Orchestrator (VCO).
- VMWare VeloCloud SD-WAN Edge - syslog


**Description:**
The CCX Splunk Add-on for VeloCloud looks to provide a single field extraction bundle for VMWare VeloCloud SD-WAN logs.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for VMWare VeloCloud SD-WAN.

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Authentication, Change, Inventory, and Network Traffic.


**Compatibility:** 

| Splunk Enterprise versions | 10, 9.4, 9.3, 9.2, 9.1 |
| --- | --- |
| CIM | 6.x 5.x |
| Platforms | Platform independent |
| Vendor Products | VeloCloud |
| Service Provider | CyberCX |

**Requirements:**

- This Add-on is intended to be installed on Splunk Search Heads and IDM/HF where data inputs is configured.
- This Technical Add-on relies on public Splunk Add-on "VCO Events to Splunk from VMware SD-WAN" (https://splunkbase.splunk.com/app/6252/) to establish API connection call to VeloCloud Orchestrator (VCO).

**Installation**

This Add-on is intended to be installed as follows:

- Splunk Cloud Victoria STACKs: Installed on Search Head

- Splunk Cloud Classic STACKs: Installed on Search Heads and IDM/HF

- Splunk Enterprise: Installed on Search Heads and Heavy Forwarders

This Add-on is intended to be installed as a companion for the following add-on:

- Install Add-on VCO Events to Splunk from VMware SD-WAN (https://splunkbase.splunk.com/app/6252) version 2.0.6 or higher

- Main sourcetype to be selected as part of inputs configuration: "ccx:velocloud:sdwan"

**Known issues:**

- none

**Release Notes:**
Version 1.0.4
- Bug fixes 
- - eventtype "ccx_velocloud_sdwanedge_syslog_traffic"
- - Calculated field "EVAL-app"