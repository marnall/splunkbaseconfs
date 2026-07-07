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

the_time=`date +%s.%3N`
csv_head='"_time"'
csv_valu="\"$the_time\""
csv_arry=(\""$the_time\"")

csv_head="$csv_head,\"metric_name:processmon.cpu.percent\""
csv_head="$csv_head,\"metric_name:processmon.memory.percent\""
csv_head="$csv_head,\"metric_name:processmon.memory.rss_kb\""
csv_head="$csv_head,\"metric_name:processmon.memory.vss_kb\""
csv_head="$csv_head,\"metric_name:processmon.uptime\""
csv_head="$csv_head,\"process_name\""
csv_head="$csv_head,\"pid\""
csv_head="$csv_head,\"user\""
csv_head="$csv_head,\"cloud\""
csv_head="$csv_head,\"region\""
csv_head="$csv_head,\"dc\""
csv_head="$csv_head,\"environment\""
csv_head="$csv_head,\"ip\""
csv_head="$csv_head,\"os\""
csv_head="$csv_head,\"os_version\""
csv_head="$csv_head,\"kernel_version\""

echo $csv_head
[[ "$(which ps 2>/dev/null)" == "" ]] && echo "Error: cannot find 'ps'" && exit 1
ps -wweo uname,pid,pcpu,pmem,rsz,vsz,etimes,comm | grep -E "(${allowlist})" | grep -Ev "(${blocklist})" | grep -v grep | while read -r line
source $current_dir/lib/dims.sh
csv_arry=(\""$the_time\"")
#Read dimensions into an array
IFS=',' read -r -a csv_dims <<< "$csv_valu"
#Remove time
unset csv_dims[0]
do
  df_device=`echo $line | awk '{print $8}'`
  processmon_pcpu=`echo $line | awk '{print $3}'`
  csv_arry+=("$processmon_pcpu")
  processmon_pmem=`echo $line | awk '{print $4}'`
  csv_arry+=("$processmon_pmem")
  processmon_rsz=`echo $line | awk '{print $5}'`
  csv_arry+=("$processmon_rsz")
  processmon_vsz=`echo $line | awk '{print $6}'`
  csv_arry+=("$processmon_vsz")
  processmon_etimes=`echo $line | awk '{print $7}'`
  csv_arry+=("$processmon_etimes")
  # Dimensions
  processmon_name=`echo $line | awk '{print $8}'`
  if [ -z "$processmon_name" ]
  then
   exit 1
  else
   csv_arry+=("\"$processmon_name\"")
  fi
  processmon_pid=`echo $line | awk '{print $2}'`
  if [ -z "$processmon_pid" ]
  then
   exit 1
  else
   csv_arry+=("\"$processmon_pid\"")
  fi
  processmon_user=`echo $line | awk '{print $1}'`
  if [ -z "$processmon_user" ]
  then
   exit 1
  else
   csv_arry+=("\"$processmon_user\"")

   csv_arra=("${csv_arry[@]}" "${csv_dims[@]}")
   (IFS=,; echo "${csv_arra[*]}")
   csv_valu="\"$the_time\""
   csv_arry=(\""$the_time\"")
  fi
done
