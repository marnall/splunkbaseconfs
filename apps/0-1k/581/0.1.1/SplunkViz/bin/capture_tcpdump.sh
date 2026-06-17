#!/bin/bash
#
# handler script for sending tcpdump data to Splunk scripted input
# 
# USAGE
#   capture_tcpdump.sh <INTERFACE_NAME>
#
#   INTERFACE_NAME
#       the name of the network interface to sniff; see ifconfig
#

if [ -z "$1" ]; then
    echo 'ERROR: missing the interface name'
    exit
fi

/usr/sbin/tcpdump -i$1 -eq
