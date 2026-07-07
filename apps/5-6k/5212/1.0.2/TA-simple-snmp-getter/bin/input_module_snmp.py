# encoding = utf-8

import os
import sys
import datetime
import time
import logging as Log

from pysnmp.hlapi import *

def getOids(host, port, community, oids):
    data = []
    for oid in oids:
        for (errorIndication,
            errorStatus,
            errorIndex,
            varBinds) in getCmd(SnmpEngine(),
                                CommunityData(community),
                                UdpTransportTarget((host, port)),
                                ContextData(),
                                ObjectType(ObjectIdentity(oid)),
                                lookupMib=False,
                                lexicographicMode=False):

            if errorIndication:
                print(errorIndication, file=sys.stderr)
                break

            elif errorStatus:
                print('%s at %s' % (errorStatus.prettyPrint(),
                                    errorIndex and varBinds[int(errorIndex) - 1][0] or '?'), file=sys.stderr)
                break

            else:
                for varBind in varBinds:
                    data.append(varBind)
    return data

def validate_input(helper, definition):
    device_ip = definition.parameters.get('device_ip', None)
    port = definition.parameters.get('port', None)
    community = definition.parameters.get('community', None)
    oids = definition.parameters.get('oids', None)
    oids_value_separator = definition.parameters.get('oids_value_separator', None)
    src_type = definition.parameters.get('src_type', None)

def collect_events(helper, ew):
    opt_device_ip = helper.get_arg('device_ip')
    opt_port = helper.get_arg('port')
    opt_community = helper.get_arg('community')
    opt_oids = helper.get_arg('oids')
    opt_oids_value_separator = helper.get_arg('oids_value_separator')
    opt_src_type = helper.get_arg('src_type')
    
    if opt_src_type == '':
        opt_src_type = 'snmp'

    oids = opt_oids.split(",")
    data = ''

    try:
        varBinds = getOids(opt_device_ip, opt_port, opt_community, oids)

        data = opt_oids_value_separator.join([str(varBind[1]) for varBind in varBinds])
    
        event = helper.new_event(data, host=None, source=None, sourcetype=opt_src_type, done=True, unbroken=True)
        ew.write_event(event)
    
    except Exception as e:
        Log.error(e)