#!/bin/bash
# get splunk path from argument
SPLUNK_HOME=$1

echo "Just restarting splunk" 2>&1 | /usr/bin/logger &
$SPLUNK_HOME/bin/splunk restart 2>&1 | /usr/bin/logger &
/usr/bin/sleep 10s
echo "Just restarted splunk" 2>&1 | /usr/bin/logger &
