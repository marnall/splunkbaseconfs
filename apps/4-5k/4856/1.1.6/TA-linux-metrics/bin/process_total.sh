#!/bin/bash
current_dir="$(dirname "$0")"

if [ -f "$current_dir/../local/process_mon.conf" ]
then
 local_process_mon="$current_dir/../local/process_mon.conf"
else
 local_process_mon=""
fi

allowlist=`grep -E "(^allowlist|^whitelist)" $current_dir/../default/process_mon.conf ${local_process_mon} | tail -1 | sed 's/,/\$| /g' | sed 's/$/\$/g' | awk -F= '{print $2}' | sed 's/^\s\+//g'`
if [ -z "$allowlist" ]
then
 allowlist="(bash$|collectd$)"
fi

blocklist=`grep -E "(^blocklist|^blacklist)" $current_dir/../default/process_mon.conf ${local_process_mon} | tail -1 | sed 's/,/\$| /g' | sed 's/$/\$/g' | awk -F= '{print $2}' | sed 's/^\s\+//g'`
if [ -z "$blocklist" ]
then
 blocklist="(nothing_to_see_here$)"
fi

[[ "$(which ps 2>/dev/null)" == "" ]] && echo "Error: cannot find 'ps'" && exit 1
COUNTER=0
# Monitored Processes
while read -r line
do
  let COUNTER++
done < <(ps -wweo uname,pid,pcpu,pmem,rsz,vsz,etimes,comm | grep -E "(${allowlist})" | grep -Ev "(${blocklist})" | grep -v grep)
processmon_counter=$COUNTER

# Total Processes
processmon_total=`ps -wweo uname,pid,pcpu,pmem,rsz,vsz,etimes,comm | tail -n+2 | wc -l`

the_time=`date +%s.%3N`
csv_head='"_time"'
csv_valu="\"$the_time\""

csv_head="$csv_head,\"metric_name:processmon.count.monitored\""
csv_head="$csv_head,\"metric_name:processmon.count.total\""
csv_head="$csv_head,\"cloud\""
csv_head="$csv_head,\"region\""
csv_head="$csv_head,\"dc\""
csv_head="$csv_head,\"environment\""
csv_head="$csv_head,\"ip\""
csv_head="$csv_head,\"os\""
csv_head="$csv_head,\"os_version\""
csv_head="$csv_head,\"kernel_version\""

echo $csv_head

csv_head='"_time"'
csv_valu="\"$the_time\""

csv_valu="$csv_valu,\"$processmon_counter\""
csv_valu="$csv_valu,\"$processmon_total\""

source $current_dir/lib/dims.sh
echo $csv_valu
