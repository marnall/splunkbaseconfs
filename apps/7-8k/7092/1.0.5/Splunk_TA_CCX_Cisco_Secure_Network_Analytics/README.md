**About Us:**
CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**
The CCX Add-on for Cisco Secure Network Analytics (Stealthwatch) looks to provide a single field extraction bundle for Cisco Secure Network Analytics logs ingested via syslog.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction TA available for Cisco Secure Network Analytics.

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**
- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Intrusion Detection (IDS), Data Loss Prevention (DLP), and Network Traffic.

**Compatibility:** 

| Splunk Enterprise versions | 9.1, 9.0, 8.2, 8.1 |
| --- | --- |
| CIM | 4.x 5.x |
| Platforms | Platform independent |
| Vendor Products | Cisco Secure Network Analytics |
| Service Provider | CyberCX |

**Requirements:**
- This Add-on is intended to be installed on Splunk Search Heads and Splunk Forwarders.

**Installation**
- This Add-on is intended to be installed on Splunk Search Heads and Splunk Forwarders.
- The main sourcetype to be used on inputs: "ccx:cisco:sna:syslog"

**Known issues:**
- none

**Recommended SNA Version:**
- Converged Analytics Engine alerting via syslog is introduced in version 7.5 (due December 2023)

**Log Format:**
 - Cisco Secure Network Analytics (Stealwatch) log pattern to be followed:

Cisco|Stealthwatch|Notification:{alarm_type_id}|{alarm_type_name}|{alarm_severity_id}|alarm_desc="{alarm_type_description}" details="{details}" dst={target_ip} src={source_ip} start={start_active_time} end={end_active_time} category={alarm_category_name} alarm_id={alarm_id} source_hg={source_host_group_names} target_hg={target_host_group_names} dpt={port} proto={protocol} device_name={device_name} device_ip={device_ip} domain_id={domain_id} signature={alarm_type_name} vendor_severity={alarm_severity_name} severity_id={alarm_severity_id} alarm_type_id={alarm_type_id} alarm_cat_id={alarm_category_id} alarm_note={alarm_note} alarm_status={alarm_status} policy_name={policy_name}
