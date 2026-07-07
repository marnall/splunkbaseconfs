#!/bin/sh

# Wrapper script called from Splunk

$SPLUNK_HOME/etc/apps/loginIDS/bin/queryDatabase.pl "$SPLUNK_HOME/etc/apps/loginIDS/local/.lastDetailedLogRead" "SELECT id, timestamp, service, userId FROM DetailedLog WHERE id > <lastPosition>;"
