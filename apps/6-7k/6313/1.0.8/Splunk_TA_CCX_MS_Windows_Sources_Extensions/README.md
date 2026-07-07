**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

The CCX Add-on CCX Microsoft Windows Sources Extensions looks to provide additional field extraction and CIM compliance for Windows log sources captured via Splunk Add-on for Microsoft Windows installed on Splunk agents (UF).

This Technical Add-on does not replace the public Splunk Add-on for Microsoft Windows (https://splunkbase.splunk.com/app/742/) but works as an additonal extension to be deployed on Search Heads (only).

Currently this add-on provides additional extraction and CIM compliance for sources:  
- XmlWinEventLog:Security (Registry)
- WinRegistry
- XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational
- WinEventLog:Microsoft-Windows-Windows Defender/Operational
- WinEventLog:Microsoft-Windows-Sysmon/Operational

Fully compatible with Splunk Enterprise and Splunk Cloud, built by an Ops team for Ops teams.

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alerts, Change, Endpoint, Network Traffic, Network Resolution (DNS), and Malware.

   
**Compatibility:** 

| Splunk Enterprise versions |  9.3, 9.2, 9.1, 9.0 |
| --- | --- |
| CIM | 5.x |
| Platforms | Platform independent |
| Service Provider | CyberCX |
| Vendor Products | MS Windows |

**Requirements:**

- This Add-on is intended to be installed on Splunk Search Heads.
- Install Add-on Splunk Add-on for Microsoft Windows (https://splunkbase.splunk.com/app/742/) version 8.4.0 or higher
- Install Add-on Splunk Add-on for Sysmon (https://splunkbase.splunk.com/app/5709) version 4.0.0 or higher

**Installation**

- This Add-on is intended to be installed on Splunk Search Heads.
- Install Add-on Splunk Add-on for Microsoft Windows (https://splunkbase.splunk.com/app/742/) version 8.4.0 or higher
- Install Add-on Splunk Add-on for Sysmon (https://splunkbase.splunk.com/app/5709) version 4.0.0 or higher - support Wineventlog Sysmon Operational log parsing 
- Recommended use of separate index for the following captured logs on Splunk UF:

Suggested configuration
###### Windows Defender Logs ######
[WinEventLog://Microsoft-Windows-Windows Defender/Operational]
disabled = 0
start_from = oldest
current_only = 0
renderXml=true
checkpointInterval = 5
index=wineventlog_defender

**Known issues:**

- Modify manually "Calculated Field": copy "Calculated Fields" search for "process_name", "user", "registry_path", and "registry_value_name" from CCX Microsoft Windows Sources Extensions Add-on into the default configuration

**Addressed Issues**

- Additional extraction and enhancements on CIM compliance fields and values for the following sources:
   XmlWinEventLog:Security (Registry)
   WinRegistry
   WinEventLog:Microsoft-Windows-Windows Defender/Operational
   XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational
   WinEventLog:Microsoft-Windows-Sysmon/Operational

