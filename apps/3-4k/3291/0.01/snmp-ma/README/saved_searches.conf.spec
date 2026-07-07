#SNMP Alerts settings

action.snmp = [0|1]
* Enabled SNMP Trap / Alerts

action.snmp.param.serverip = <string>
* The SNMP Server IP that will receive the message
* (required)

action.snmp.param.port = <integer>
* The port of the SNMP trap
* (required)

action.snmp.param.community = <string>
* The community of the SNMP trap
* (required)

action.snmp.param.mibname = <string>
* The MIB Name of the SNMP trap
* (required)

action.snmp.param.mibobject = <string>
* The MIB Object of the SNMP trap
* (required)
