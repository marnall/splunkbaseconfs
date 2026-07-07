import sys
import os

from splunklib.modularinput import *
from pysnmp.entity.rfc3413.oneliner import cmdgen
import json

class NimbleSNMP(Script):

    def get_scheme(self):
        # Setup scheme.
        scheme = Scheme("Nimble Array SNMP Counters")
        scheme.description = "Streams information about array from Nimble via SNMP"
        scheme.use_external_validation = True

        #Add arguments
        array_argument = Argument("array")
        array_argument.data_type = Argument.data_type_string
        array_argument.description = "Host or IP Address of Nimble Array"
        array_argument.required_on_create = True
        scheme.add_argument(array_argument)

        port_argument = Argument("port")
        port_argument.data_type = Argument.data_type_string
        port_argument.description = "Nimble SNMP port"
        port_argument.required_on_create = True
        scheme.add_argument(port_argument)

        community_argument = Argument("community")
        community_argument.data_type = Argument.data_type_string
        community_argument.description = "Nimble SNMP Community"
        community_argument.required_on_create = True
        scheme.add_argument(community_argument)

        return scheme

    def stream_events(self, inputs, ew):
        # Splunk Enterprise calls the modular input, 
        # streams XML describing the inputs to stdin,
        # and waits for XML on stdout describing events.
        for input_name,input_item in inputs.inputs.iteritems():
            ew.log("INFO","Starting input")
            ARRAY = input_item["array"]
            PORT = input_item["port"]
            COMMUNITY = input_item["community"]
            ew.log("INFO", 'ARRAY=%s COMMUNITY=%s PORT=%s' % (ARRAY,COMMUNITY,PORT))

            cmdGen = cmdgen.CommandGenerator()
            errorIndication, errorStatus, errorIndex, varBindTable = cmdGen.bulkCmd(
                cmdgen.CommunityData(COMMUNITY),
                cmdgen.UdpTransportTarget((ARRAY, 161)),
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
                    print(json.dumps(globalmibs, sort_keys=True,indent=4, separators=(',', ': ')))
                    for key in volumes:
                        raw_event = Event()
                        raw_event.stanza = "%s:volume:%s" % (input_name,key)
                        raw_event.host = ARRAY
                        raw_event.data = json.dumps(volumes[key])
                        raw_event.sourcetype = 'nimble:snmp:volume_detail'
                        raw_event.source = "snmp:volume:%s" % (key)
                        ew.write_event(raw_event)
                    raw_event = Event()
                    raw_event.stanza = "%s:global" % (input_name)
                    raw_event.host = ARRAY
                    raw_event.data = json.dumps(globalmibs)
                    raw_event.sourcetype = "nimble:snmp:global"
                    raw_event.source = "snmp:global"
                    ew.write_event(raw_event)


if __name__ == "__main__":
    sys.exit(NimbleSNMP().run(sys.argv))