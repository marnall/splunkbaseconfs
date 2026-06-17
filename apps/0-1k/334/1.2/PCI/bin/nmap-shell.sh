#!/bin/bash

OUTPUT="/home/chuck/splunk-inputs/nmap-scans"
TMP="/tmp/nmap.tmp"
NET="192.168.2.0/24"

set $(date)
nmap -oG $TMP $NET
cat $TMP | grep Host|awk -F'(' '{print $1 $2}'|awk -F')' '{print $1 $2}'|awk -F"Ports:" '{print $1 $2}' >> $OUTPUT/$6-$2-$3.log
rm -f $NET
