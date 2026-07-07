#!/bin/bash
current_dir="$(dirname "$0")"

# Exclude these filesystem types
df_options="-P -i -x tmpfs -x squashfs -x devtmpfs -x sr0 -x vfat -x fd0"

[[ "$(which df 2>/dev/null)" == "" ]] && echo "Error: cannot find 'df'" && exit 1

# Filesystem                                     Type   Inodes IUsed    IFree IUse% Mounted on
# /dev/mapper/s1tlispk33std_rootvg-rootlv        xfs   2048000 45585  2002415    3% /

the_time=`date +%s.%3N`
csv_head='"_time"'
csv_valu="\"$the_time\""

csv_head="$csv_head,\"metric_name:df.inode.total\""
csv_head="$csv_head,\"metric_name:df.inode.used\""
csv_head="$csv_head,\"metric_name:df.inode.pctused\""
csv_head="$csv_head,\"metric_name:df.inode.free\""
csv_head="$csv_head,\"metric_name:df.inode.pctfree\""
csv_head="$csv_head,\"device\""
csv_head="$csv_head,\"mountpoint\""
csv_head="$csv_head,\"type\""
csv_head="$csv_head,\"cloud\""
csv_head="$csv_head,\"region\""
csv_head="$csv_head,\"dc\""
csv_head="$csv_head,\"environment\""
csv_head="$csv_head,\"ip\""
csv_head="$csv_head,\"os\""
csv_head="$csv_head,\"os_version\""
csv_head="$csv_head,\"kernel_version\""

echo $csv_head

while read line
do
  df_total=`echo $line | awk '{print $3}'`
  if [ -z "$df_total" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$df_total"
  fi
  df_used=`echo $line | awk '{print $4}'`
  df_usepct=$(awk -v u=$df_used -v t=$df_total 'BEGIN { print ((u / t) * 100) }')
  if [ -z "$df_usepct" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$df_used,$df_usepct"
  fi
  df_free=`echo $line | awk '{print $5}'`
  df_freepct=$(awk -v a=$df_free -v t=$df_total 'BEGIN { print ((a / t) * 100) }')
  if [ -z "$df_freepct" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$df_free,$df_freepct"
  fi
  df_device=`echo $line | awk '{print $1}' | grep -Po '\/dev(/\w+|)\/\K(.+)'`
  if [ -z "$df_device" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,\"$df_device\""
  fi
  df_mp=`echo $line | awk '{print $7}'`
  if [ -z "$df_mp" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,\"$df_mp\""
  fi
  df_type=`echo $line | awk '{print $2}'`
  if [ -z "$df_type" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,\"$df_type\""
   source $current_dir/lib/dims.sh

   echo $csv_valu
   csv_valu="\"$the_time\""
  fi
done < <(df -P -T $df_options | grep -v ^Filesystem)
