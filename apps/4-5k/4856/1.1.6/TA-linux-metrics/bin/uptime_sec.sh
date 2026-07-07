#!/bin/bash
current_dir="$(dirname "$0")"

the_time=`date +%s.%3N`
csv_head='"_time"'
csv_valu="\"$the_time\""

uptime=`awk '{print $1}' /proc/uptime`
if [ -z "$uptime" ]
then
 uptime2=0.0
 csv_head="$csv_head,\"metric_name:uptime.uptime\""
 csv_valu="$csv_valu,$uptime2"
else
 uptime2=$uptime
 csv_head="$csv_head,\"metric_name:uptime.uptime\""
 csv_valu="$csv_valu,$uptime2"
fi

source $current_dir/lib/dims.sh

echo $csv_head
echo $csv_valu
