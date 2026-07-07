#!/bin/bash
# Matt Kirby
# 2012-10-31


umask 0077
scriptname=${0##*/}
/opt/splunk/etc/apps/LogCompactor/bin/syslogcompactor.pl --report=$SPLUNK_ARG_8 --emailto='administrator@localhost' --emailfrom='logcompactor@localhost' --smtpserver='localhost' --name="$SPLUNK_ARG_4" --link="$SPLUNK_ARG_6" --threshold=1 >/tmp/${scriptname%%.sh}.log 2>&1


