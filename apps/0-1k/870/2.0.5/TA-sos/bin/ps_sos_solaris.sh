#!/bin/sh
# Copyright (C) 2013 Splunk
# Vainstein K 25feb2013

[ -z "$SPLUNK_HOME" ] && echo 'The SPLUNK_HOME env var is not set; cannot continue.' >&2 && exit 1

PID_SPLUNKD=`sed q $SPLUNK_HOME/var/run/splunk/splunkd.pid 2>/dev/null`
[ -z "$PID_SPLUNKD" ] && echo 'splunkd.pid not found' >&2 && PID_SPLUNKD=0

PID_SPLUNKWEB=`cat $SPLUNK_HOME/var/run/splunk/splunkweb.pid 2>/dev/null`
[ -z "$PID_SPLUNKWEB" ] && echo 'splunkweb.pid not found' >&2 && PID_SPLUNKWEB=0

HEADER='USER               PID   PSR   pctCPU       CPUTIME  pctMEM     RSZ_KB     VSZ_KB   TTY      S       ELAPSED  COMMAND             ARGS'
HEADERIZE='{print $0}'
GET_NICE_ARGS='{while ("/usr/ucb/ps auxwww | /usr/xpg4/bin/grep -e 'splunkd' -e 'python' | grep -v grep" | getline) {pid=$2; cmd=""; want = 0; for (i=6;i<=NF;i++) {want = want || index($i, "splunk"); if (want) cmd = cmd " " $i} anice[pid]=cmd}}'
WHILE_OPEN='while ("/usr/bin/ps -eo user,pid,psr,pcpu,time,pmem,rss,vsz,tty,s,etime,args" | getline) { if (! usr_ucb_ps_headerSkipped) {usr_ucb_ps_headerSkipped=1; continue}'
FORMAT_OTHER='{sub("^_", "", $1); sub("^[^\134[: -]*/", "", $12)}'
FORMAT_ARGS='{if ($2 in anice) {args=anice[$2]; gsub(" ", "_", args)} else if (NF>12) {args=$13; for (j=14; j<=NF; j++) args = args "_" $j} else args="<noArgs>"}'
FILTER='{if (!( ($2 == '$PID_SPLUNKD') || ($2 == '$PID_SPLUNKWEB') || (args ~ /_search_--id=/))) continue}'
NORMALIZE='{if ($4<0 || $4>100) $4=0; if ($6<0 || $6>100) $6=0}'
PRINTF='{printf "%-14.14s  %6s  %4s   %6s  %12s  %6s   %8s   %8s   %-7.7s  %1.1s  %12s  %-18.18s  %s\n", $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, args}'
WHILE_CLOSE='}'

echo "$HEADER" | nawk "{ $HEADERIZE $GET_NICE_ARGS $WHILE_OPEN $FORMAT_OTHER $FORMAT_ARGS $FILTER $NORMALIZE $PRINTF $WHILE_CLOSE }"
