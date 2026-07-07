### SCRIPT NAME: snmp.py
### AUTHOR: Michael Camp Bentley aka JKat54 (JKat54 at datashepherds.com)
### Copyright 2016 Michael Camp Bentley
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###    http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###
### Description: A Splunk Modular Alert Add-on which allows you to send SNMP TRAPs directly from Splunk.  

import sys
import json
from pysnmp.hlapi import *
import splunk.Intersplunk
import splunk.mining.dcutils as dcu


logger = dcu.getLogger()
   
def execute():
  try:
    # get the arguments suplied
    payload = json.loads(sys.stdin.read())
    config = payload.get('configuration', dict())
    splunkapp = payload.get('app')
    splunksearch = payload.get('search_name')
    serverip = config.get('serverip')
    port = str(config.get('port'))
    community = config.get('community')
    mibname = config.get('mibname')
    mibobject = config.get('mibobject')

    # log the objects supplied
    logger.info(
               "splunkapp: " + str(splunkapp)
               + ", splunksearch: " + str(splunksearch)
               + ", snmp_server: " + str(serverip) 
               + ", snmp_port: " + str(port)
               + ", snmp_community: " + str(community)
               + ", snmp_mibname: " + str(mibname)
               + ", snmp_mibobject: " + str(mibobject)   
               )

    errorIndication, errorStatus, errorIndex, varBinds = next(
    sendNotification(
        SnmpEngine(),
        CommunityData(community),
        UdpTransportTarget((serverip, port)),
        ContextData(),
        'trap',
        NotificationType(ObjectIdentity(mibname, mibobject))
        )
    )

  except Exception, e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults(str(e))
    logger.error(str(e) + ". Traceback: " + str(stack))

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
    execute()

