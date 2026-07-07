from pysnmp.entity.rfc3413.oneliner import cmdgen
import json

cmdGen = cmdgen.CommandGenerator()
errorIndication, errorStatus, errorIndex, varBindTable = cmdGen.bulkCmd(
cmdgen.CommunityData('public'),
cmdgen.UdpTransportTarget(('104.197.6.41', 161)),
0, 25,
'1.3.6.1.4.1.37447'
)

if errorIndication:
    print(errorIndication)
else:
    if errorStatus:
        print('%s at %s' % (
            errorStatus.prettyPrint(),
            errorIndex and varBindTable[-1][int(errorIndex)-1] or '?'
            )
        )
    else:
        volumes = {}
        globalmibs = {}
        for varBindTableRow in varBindTable:
            for name, val in varBindTableRow:
                strName = str(name)
                if strName.startswith("1.3.6.1.4.1.37447.1.2.1."):
                    keys = strName.split(".")
                    vol = int(keys[11])
                    attribute = keys[10]
                    if not(vol in volumes):
                        volumes[vol] = {}
                    volumes[vol][attribute] = val.prettyPrint()
                else:
                    keys = strName.split(".")
                    attribute = keys[9]
                    globalmibs[attribute] = val.prettyPrint()
        for key in volumes:
            print "snmp:volume:%s=%s" % (key,json.dumps(volumes[key]))

        print json.dumps(globalmibs)