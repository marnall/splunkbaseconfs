#!/bin/bash
current_dir="$(dirname "$0")"

cat /proc/loadavg > /tmp/loadavg

the_time=`date +%s.%3N`
csv_head='"_time"'
csv_valu="\"$the_time\""

load_short=`awk '{print $1}' /tmp/loadavg`
if [ -z "$load_short" ]
then
 load_short2=0.0
 csv_head="$csv_head,\"metric_name:load.shortterm\""
 csv_valu="$csv_valu,$load_short2"
else
 load_short2=$load_short
 csv_head="$csv_head,\"metric_name:load.shortterm\""
 csv_valu="$csv_valu,$load_short2"
fi

load_mid=`awk '{print $2}' /tmp/loadavg`
if [ -z "$load_mid" ]
then
 load_mid2=0.0
 csv_head="$csv_head,\"metric_name:load.midterm\""
 csv_valu="$csv_valu,$load_mid2"
else
 load_mid2=$load_mid
 csv_head="$csv_head,\"metric_name:load.midterm\""
 csv_valu="$csv_valu,$load_mid2"
fi

load_long=`awk '{print $3}' /tmp/loadavg`
if [ -z "$load_long" ]
then
 load_long2=0.0
 csv_head="$csv_head,\"metric_name:load.longterm\""
 csv_valu="$csv_valu,$load_long2"
else
 load_long2=$load_long
 csv_head="$csv_head,\"metric_name:load.longterm\""
 csv_valu="$csv_valu,$load_long2"
fi

load_procs=`awk '{print $4}' /tmp/loadavg`
load_procs_current=`echo $load_procs | awk -F\/ '{print $1}'`
if [ -z "$load_procs_current" ]
then
 load_procs_current2=0
 csv_head="$csv_head,\"metric_name:load.procs_current\""
 csv_valu="$csv_valu,$load_procs_current2"
else
 load_procs_current2=$load_procs_current
 csv_head="$csv_head,\"metric_name:load.procs_current\""
 csv_valu="$csv_valu,$load_procs_current2"
fi

load_procs_total=`echo $load_procs | awk -F\/ '{print $2}'`
if [ -z "$load_procs_total" ]
then
 load_procs_total2=0
 csv_head="$csv_head,\"metric_name:load.procs_total\""
 csv_valu="$csv_valu,$load_procs_total2"
else
 load_procs_total2=$load_procs_total
 csv_head="$csv_head,\"metric_name:load.procs_total\""
 csv_valu="$csv_valu,$load_procs_total2"
fi

source $current_dir/lib/dims.sh

echo $csv_head
echo $csv_valu

rm -f /tmp/loadavg
