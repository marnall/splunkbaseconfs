[global]
* ### Threat Control
action.sentinelone-threat-control                       = [0|1]
* Enable sentinelone-threat-control Actions
action.sentinelone-threat-control.param.incident_status = <string>
action.sentinelone-threat-control.param.verdict         = <string>
action.sentinelone-threat-control.param.mgmt_host       = <string>
action.sentinelone-threat-control.param.site_id         = <string>
action.sentinelone-threat-control.param.threat_id       = <string>
action.sentinelone-threat-control.param._cam            = <object>
* ### Network Control
action.sentinelone-network-control                      = [0|1]
* Enable sentinelone-network-control Actions
action.sentinelone-network-control.param.site_id        = <string>
action.sentinelone-network-control.param.mgmt_host      = <string>
action.sentinelone-network-control.param.network_action = <string>
action.sentinelone-network-control.param.agent_id       = <string>
action.sentinelone-network-control.param._cam           = <object>
action.sentinelone-s1query-send-event                  = [0|1]
* Create S1Query Event
action.sentinelone-s1query-send-event.param._cam       = <object>
* Common Alert Model configuration object.
action.sentinelone-s1query-send-event.param.severity   = <string>
* S1Query Severity
action.sentinelone-s1query-send-event.param.message    = <string>
* S1Query message body
action.sentinelone-s1query-send-event.param.parser     = <string>
action.sentinelone-s1query-send-event.param.credential = <string>
action.sentinelone-s1query-send-event.param.auth_hosts = <string>
* No Help Defined.
action.sentinelone-s1query-send-event.param.proxy_guid = <string>
* No Help Defined.