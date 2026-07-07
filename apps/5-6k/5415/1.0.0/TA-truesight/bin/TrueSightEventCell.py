#!/usr/bin/python
# -*- coding: utf-8 -*-


#Splunk Custom Alert Action for BMC Patrol
#Send dynamic alerts via the MSEND command
#https://docs.bmc.com/docs/display/public/btsim96/mposter+and+msend+syntax
#Jeff Weiderman cleaned up the mess Matthew Modestino made 09.2016
#Thanks to Sean Mullen for pushing it over the goal line! 01.2017
#https://github.com/n00badmin/splunk_alert_bmcpatrol

import sys
import re
import subprocess
import json
import csv
import gzip

#Check args
def main():
    #get json ouptut from splunk modular alert - See alert_actions.conf.spec
    payload = json.loads(sys.stdin.read())
    config = payload.get('configuration', dict())
    cell =  config.get('cell')
    #host = payload.get('host') 
    host = ""
    splunkServer = payload.get('server_host')
    splunkURI = payload.get('server_uri')
    splunkApp = payload.get('app')
    splunkSearch = payload.get('search_name')
    resultsLink = payload.get('results_link')
    result = payload.get('result')
    bmcPatrolTargetURI = config.get('targetURI')
    message = config.get('message')
    severity = config.get('severity')
    mc_object = config.get('object')
    hostname = config.get('hostname')
    #use contents of body to dynamically populate, then execute the MSEND CLI command
    #msendcmd = '/root/msend -n @{0}#mc -a EVENT -r "{1}" -m "{2}" -b "mc_host={3};mc_tool_class=SPLUNK-ENTERPRISE;mc_object={4};mc_object_owner=test;mc_tool={5};mc_tool_uri={6}"'
    msendcmd = './msend -n @{0}#mc -a SPLUNK_EV -r "{1}" -m "{2}" -b "mc_host={3};mc_tool_class=SPLUNK-ENTERPRISE;mc_object={4};mc_object_owner=test;mc_tool={5};mc_tool_uri={6}"'
    msendcmd = msendcmd.format(cell, severity, message, hostname, mc_object, splunkSearch, resultsLink)
    
    #UNCOMMENT DEBUG
    ps = open("/tmp/bmc.out","w")
    ps.write("msendcmd = " + msendcmd  +"\n")
    ps.write("eventcell = " +  cell + "\n")

    try:
        msend = subprocess.check_output(msendcmd, shell=True)
        sys.stdout.write(msend); 
    except:
        sys.stderr.write('[bppm] failed to run MSEND command\n')
        sys.stderr.write('[bppm] {0}\n'.format(msendcmd))
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
         print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
         sys.exit(1)
    
    main()

