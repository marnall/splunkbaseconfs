#!/bin/sh

# Wrapper script called from Splunk

$SPLUNK_HOME/etc/apps/loginIDS/bin/queryDatabase.pl "$SPLUNK_HOME/etc/apps/loginIDS/local/.lastAlertRead" "SELECT a.id, a.timestamp, a.falsePositive, at.name, l.service, l.source, l.destination, u.loginName, u.id FROM Alerts a JOIN AlertTypes at ON a.type=at.id JOIN Users u ON a.userId=u.id JOIN LongtimeLog l ON a.longtimeLogId=l.id WHERE a.id > <lastPosition>;"
