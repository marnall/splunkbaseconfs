#!/bin/sh

# Wrapper script called from Splunk

$SPLUNK_HOME/etc/apps/loginIDS/bin/queryDatabase.pl "$SPLUNK_HOME/etc/apps/loginIDS/local/.lastLongtimeLogEntryRead" "SELECT id, userId, service, source, destination FROM LongtimeLog WHERE id > <lastPosition>;"
