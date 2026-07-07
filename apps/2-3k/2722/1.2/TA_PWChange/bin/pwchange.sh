#!/bin/bash
$SPLUNK_HOME/bin/splunk edit user admin -password `head -c 500 /dev/urandom | sha256sum | base64 | head -c 16 ; echo` -auth admin:changeme
echo "pwchange ran on `hostname`!"
rm -frv $SPLUNK_HOME/etc/apps/TA_PWChange
