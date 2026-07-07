#!/bin/sh

# Wrapper script called from Splunk

$SPLUNK_HOME/etc/apps/loginIDS/bin/queryDatabase.pl "$SPLUNK_HOME/etc/apps/loginIDS/local/.lastAccessTimeRead" "SELECT id, day, hour, type, longtimeLogId FROM AccessTimeDetails WHERE id > <lastPosition>;"
