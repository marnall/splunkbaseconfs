#!/bin/bash

export DATE=`date "+%m-%d-%Y %H:%M:%S.%3N %z"`
export HOSTNAME=`hostname`
export SPLUNK_HOME=/opt/splunkforwarder

echo $DATE INFO $HOSTNAME "Initializing Fix Hostname!" >> $SPLUNK_HOME/var/log/splunk/Fix_HostName_for_Splunk.log

echo $DATE INFO $HOSTNAME "Stopping the service splunk..." >> $SPLUNK_HOME/var/log/splunk/Fix_HostName_for_Splunk.log
$SPLUNK_HOME/bin/splunk stop >> $SPLUNK_HOME/var/log/splunk/Fix_HostName_for_Splunk.log

echo $DATE INFO $HOSTNAME "Running the clear config..." >> $SPLUNK_HOME/var/log/splunk/Fix_HostName_for_Splunk.log
$SPLUNK_HOME/bin/splunk clone-prep-clear-config >> $SPLUNK_HOME/var/log/splunk/Fix_HostName_for_Splunk.log

echo $DATE INFO $HOSTNAME "Removing the package..." >> $SPLUNK_HOME/var/log/splunk/Fix_HostName_for_Splunk.log
rm -rf $SPLUNK_HOME/etc/apps/Fix_HostName_for_Splunk >> $SPLUNK_HOME/var/log/splunk/Fix_HostName_for_Splunk.log

echo $DATE INFO $HOSTNAME "Initializing the service splunk..." >> $SPLUNK_HOME/var/log/splunk/Fix_HostName_for_Splunk.log
$SPLUNK_HOME/bin/splunk start >> $SPLUNK_HOME/var/log/splunk/Fix_HostName_for_Splunk.log 2>&1

echo $DATE INFO $HOSTNAME "Finishing Fix Hostname!" >> $SPLUNK_HOME/var/log/splunk/Fix_HostName_for_Splunk.log
