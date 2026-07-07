

[sentinelone-threat-control]
param._cam            = <value>
* CIM Actions / Adaptive Response Requirement
param.auth_hosts      = <value>
* Comma Separated Auth Host Guids allowed to use this command
param.incident_status = <list>
* Incident status for the threat
param.verdict         = <list>
* Analysis verdict for the threat
param.site_id         = <string>
* Site id
param.threat_id       = <string>
* Threat id
param.mgmt_host       = <string>
* Host
param.proxy_guid      = <value>
* The Proxy Guid to use
param.verify_ssl      = <value>
* Verify SSL
description           = <value>
* Description of the alert action

[sentinelone-network-control]
param._cam           = <value>
* CIM Actions / Adaptive Response Requirement
param.auth_hosts     = <value>
* Comma Separated Auth Host Guids allowed to use this command
param.network_action = <list>
* Action to be taken on threat
param.site_id        = <string>
* Site id
param.agent_id       = <string>
* Agent id
param.mgmt_host      = <string>
* Host
param.proxy_guid     = <value>
* The Proxy Guid to use
param.verify_ssl     = <value>
* Verify SSL
description          = <value>

[sentinelone-s1query-send-event]
param._cam       = <object>
* Common Alert Model configuration object.
param.severity   = <string>
* S1Query Severity
param.message    = <string>
* S1Query message body
param.parser     = <string>
param.credential = <string>
param.auth_hosts = <string>
* No Help Defined.
param.proxy_guid = <string>
* No Help Defined.