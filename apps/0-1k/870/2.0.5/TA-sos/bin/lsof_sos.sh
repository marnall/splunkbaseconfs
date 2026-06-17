#!/bin/sh 
# Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
# Vainstein K 14may2009
# Edited by Wiggy 08june2012

. `dirname $0`/common.sh

HEADER='COMMAND     PID        USER   FD      TYPE             DEVICE     SIZE       NODE NAME'
HEADERIZE='{NR == 1 && $0 = header}'
PID_SPLUNKD=`sed q $SPLUNK_HOME/var/run/splunk/splunkd.pid 2>/dev/null`
PID_SPLUNKWEB=`cat $SPLUNK_HOME/var/run/splunk/splunkweb.pid 2>/dev/null`
if [ "x" = "x$PID_SPLUNKD" ]; then PID_SPLUNKD=0; fi
if [ "x" = "x$PID_SPLUNKWEB" ]; then PID_SPLUNKWEB=0; fi
CMD='lsof -n -P -s -p $PID_SPLUNKD,$PID_SPLUNKWEB'
PRINTF='{printf "%-15.15s  %-10s  %-15.15s  %-8s %-8s  %-15.15s  %15s  %-20.20s  %-s\n", $1,$2,$3,$4,$5,$6,$7,$8,$9}'

if [ "x$KERNEL" = "xLinux" ] ; then
        FILTER='/Permission denied/ {next} {if ($4 == "NOFD" || $5 == "unknown") next}'
        FILL_BLANKS='{if (NF<9) {node=$7; name=$8; $7="?"; $8=node; $9=name}}'
elif [ "x$KERNEL" = "xSunOS" ] ; then
        failUnsupportedScript
elif [ "x$KERNEL" = "xDarwin" ] ; then
        FILTER='{if ($5 ~ /KQUEUE|PIPE|PSXSEM/) next}'
        FILL_BLANKS='{if (NF<9) {name=$8; $8="?"; $9=name}}'
elif [ "x$KERNEL" = "xFreeBSD" ] ; then
        failUnsupportedScript
fi

assertHaveCommand $CMD
eval $CMD | tee $TEE_DEST | awk "$HEADERIZE $FILTER $FILL_BLANKS $PRINTF" header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$HEADERIZE $FILL_BLANKS $FORMAT $NORMALIZE $FILTER $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
