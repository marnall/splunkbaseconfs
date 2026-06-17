#!/bin/sh
# Copyright (C) 2010 Binary ARP Limited.  All Rights Reserved.
# P Bassill 1aug2010

. `dirname $0`/common.sh

HEADER='Filesystem                                          Type              Size        Used       Avail      UsePct    MountedOn'
HEADERIZE='{if (NR==1) {$0 = header}}'
PRINTF='{printf "%-50s  %-10s  %10s  %10s  %10s  %10s    %s\n", $1, $2, $3, $4, $5, $6, $7}'

if [ "x$KERNEL" = "xLinux" ] ; then
	assertHaveCommand nmap
	CMD='nmap -oG /tmp/nmap.tmp 192.168.2.0/24'
	FILTER_POST='($2 ~ /^(tmpfs)$/) {next}'
fi

$CMD | tee $TEE_DEST | $AWK "$HEADERIZE $FILTER_PRE $MAP_FS_TO_TYPE $FORMAT $FILTER_POST $NORMALIZE $PRINTF"  header="$HEADER"
echo "Cmd = [$CMD];  | $AWK '$HEADERIZE $FILTER_PRE $MAP_FS_TO_TYPE $FORMAT $FILTER_POST $NORMALIZE $PRINTF' header=\"$HEADER\"" >> $TEE_DEST
