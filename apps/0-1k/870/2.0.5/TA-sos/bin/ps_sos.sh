#!/bin/sh
# Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
# Vainstein K 25aug2011

. `dirname $0`/common.sh

HEADER='USER               PID   PSR   pctCPU       CPUTIME  pctMEM     RSZ_KB     VSZ_KB   TTY      S       ELAPSED  COMMAND             ARGS'
FORMAT='{sub("^_", "", $1); if (NF>12) {args=$13; for (j=14; j<=NF; j++) args = args "_" $j} else args="<noArgs>"; sub("^[^\134[: -]*/", "", $12)}'
NORMALIZE='(NR>1) {if ($4<0) $4=0; if ($6<0 || $6>100) $6=0}'
PID_SPLUNKD=`sed q $SPLUNK_HOME/var/run/splunk/splunkd.pid 2>/dev/null`
PID_SPLUNKWEB=`cat $SPLUNK_HOME/var/run/splunk/splunkweb.pid 2>/dev/null`
if [ "x" = "x$PID_SPLUNKD" ]; then PID_SPLUNKD=0; fi
if [ "x" = "x$PID_SPLUNKWEB" ]; then PID_SPLUNKWEB=0; fi
FILTER='((NR > 1) && !(($2 == '$PID_SPLUNKD') || ($2 == '$PID_SPLUNKWEB') || ($0 ~ /splunkd[ ]*search/) || ($0 ~ /\[splunkd[ ]*pid=[0-9]*\] search/))) {next}'
PRINTF='{if (NR == 1) {print $0} else {printf "%-14.14s  %6s  %4s   %6s  %12s  %6s   %8s   %8s   %-7.7s  %1.1s  %12s  %-18.18s  %s\n", $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, args}}'

HEADERIZE='{NR == 1 && $0 = header}'
CMD='ps auxww'

if [ "x$KERNEL" = "xLinux" ] ; then
	assertHaveCommand ps
	CMD='ps -wweo uname,pid,psr,pcpu,cputime,pmem,rsz,vsz,tty,s,etime,args'
elif [ "x$KERNEL" = "xSunOS" ] ; then
#	assertHaveCommandGivenPath /usr/bin/ps
#	CMD='/usr/bin/ps -eo user,pid,psr,pcpu,time,pmem,rss,vsz,tty,s,etime,args'
	. `dirname $0`/ps_sos_solaris.sh
	exit 0
elif [ "x$KERNEL" = "xDarwin" ] ; then
	assertHaveCommand ps
	CMD='ps axo ruser,pid,pcpu,cputime,pmem,rss,vsz,tty,state,etime,command'
	FILL_BLANKS='{if (NR>1) {for (i=NF; i>2; i--) $(i+1) = $i; $3 = "?"}}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
	assertHaveCommand ps
	CMD='ps axo ruser,pid,pcpu,cputime,pmem,rss,vsz,tty,state,etime,command'
	FILL_BLANKS='{if (NR>1) {for (i=NF; i>2; i--) $(i+1) = $i; $3 = "?"}}'
fi

eval $CMD | tee $TEE_DEST | $AWK "$HEADERIZE $FILL_BLANKS $FORMAT $NORMALIZE $FILTER $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$HEADERIZE $FILL_BLANKS $FORMAT $NORMALIZE $FILTER $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
