#!/bin/bash
current_dir="$(dirname "$0")"

cat /proc/diskstats | grep -v loop > /tmp/diskstats

the_time=`date +%s.%3N`
csv_head='"_time"'
csv_valu="\"$the_time\""

csv_head="$csv_head,\"metric_name:disk.ops.read\""
csv_head="$csv_head,\"metric_name:disk.merged.read\""
csv_head="$csv_head,\"metric_name:disk.octets.read\""
csv_head="$csv_head,\"metric_name:disk.time.read\""
csv_head="$csv_head,\"metric_name:disk.ops.write\""
csv_head="$csv_head,\"metric_name:disk.merged.write\""
csv_head="$csv_head,\"metric_name:disk.octets.write\""
csv_head="$csv_head,\"metric_name:disk.time.write\""
csv_head="$csv_head,\"metric_name:disk.pending_operations\""
csv_head="$csv_head,\"metric_name:disk.io_time.io_time\""
csv_head="$csv_head,\"metric_name:disk.io_time.weighted_io_time\""
csv_head="$csv_head,\"disk\""
csv_head="$csv_head,\"disk_type\""
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
  df_device=`echo $line | awk '{print $3}'`
  if [ -z "$df_device" ]
  then
   exit 1
  fi
  disk_opsr=`echo $line | awk '{print $4}'`
  if [ ! -f "/tmp/diskstats2" ]
  then
   disk_opsr=0
   disk_opsr2=0
   disk_opsrv=0
  else
   disk_opsr2=`grep "$df_device " /tmp/diskstats2 | awk '{print $4}'`
   the_time2=`grep the_time /tmp/diskstats2 | awk -F= '{print $2}'`
   the_diff=$(awk -v a=$disk_opsr -v b=$disk_opsr2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    disk_opsrv=0
   else
    disk_opsrv=$(awk -v a=$disk_opsr -v b=$disk_opsr2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$disk_opsrv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$disk_opsrv"
  fi
  disk_mrgr=`echo $line | awk '{print $5}'`
  if [ ! -f "/tmp/diskstats2" ]
  then
   disk_mrgr=0
   disk_mrgr2=0
   disk_mrgrv=0
  else
   disk_mrgr2=`grep "$df_device " /tmp/diskstats2 | awk '{print $5}'`
   the_diff=$(awk -v a=$disk_mrgr -v b=$disk_mrgr2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    disk_mrgrv=0
   else
    disk_mrgrv=$(awk -v a=$disk_mrgr -v b=$disk_mrgr2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$disk_mrgrv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$disk_mrgrv"
  fi
  disk_octr=`echo $line | awk '{print $6}'`
  if [ ! -f "/tmp/diskstats2" ]
  then
   disk_octr=0
   disk_octr2=0
   disk_octrv=0
  else
   disk_octr2=`grep "$df_device " /tmp/diskstats2 | awk '{print $6}'`
   the_diff=$(awk -v a=$disk_octr -v b=$disk_octr2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    disk_octrv=0
   else
       disk_octrv=$(awk -v a=$disk_octr -v b=$disk_octr2 -v c=$the_time -v d=$the_time2 'BEGIN { print (((a - b) * 512) / (c - d)) }')
   fi
  fi
  if [ -z "$disk_octrv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$disk_octrv"
  fi
  disk_timr=`echo $line | awk '{print $7}'`
  if [ ! -f "/tmp/diskstats2" ]
  then
   disk_timr=0
   disk_timr2=0
   disk_timrv=0
  else
   disk_timr2=`grep "$df_device " /tmp/diskstats2 | awk '{print $7}'`
   the_diff=$(awk -v a=$disk_timr -v b=$disk_timr2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    disk_timrv=0
   else
    disk_timrv=$(awk -v a=$disk_timr -v b=$disk_timr2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$disk_timrv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$disk_timrv"
  fi
  disk_opsw=`echo $line | awk '{print $8}'`
  if [ ! -f "/tmp/diskstats2" ]
  then
   disk_opsw=0
   disk_opsw2=0
   disk_opswv=0
  else
   disk_opsw2=`grep "$df_device " /tmp/diskstats2 | awk '{print $8}'`
   the_diff=$(awk -v a=$disk_opsw -v b=$disk_opsw2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    disk_opswv=0
   else
    disk_opswv=$(awk -v a=$disk_opsw -v b=$disk_opsw2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$disk_opswv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$disk_opswv"
  fi
  disk_mgrw=`echo $line | awk '{print $9}'`
  if [ ! -f "/tmp/diskstats2" ]
  then
   disk_mgrw=0
   disk_mgrw2=0
   disk_mgrwv=0
  else
   disk_mgrw2=`grep "$df_device " /tmp/diskstats2 | awk '{print $9}'`
   the_diff=$(awk -v a=$disk_mgrw -v b=$disk_mgrw2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    disk_mgrwv=0
   else
    disk_mgrwv=$(awk -v a=$disk_mgrw -v b=$disk_mgrw2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$disk_mgrwv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$disk_mgrwv"
  fi
  disk_octw=`echo $line | awk '{print $10}'`
  if [ ! -f "/tmp/diskstats2" ]
  then
   disk_octw=0
   disk_octw2=0
   disk_octwv=0
  else
   disk_octw2=`grep "$df_device " /tmp/diskstats2 | awk '{print $10}'`
   the_diff=$(awk -v a=$disk_octw -v b=$disk_octw2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    disk_octwv=0
   else
       disk_octwv=$(awk -v a=$disk_octw -v b=$disk_octw2 -v c=$the_time -v d=$the_time2 'BEGIN { print (((a - b) * 512) / (c - d)) }')
   fi
  fi
  if [ -z "$disk_octwv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$disk_octwv"
  fi
  disk_timw=`echo $line | awk '{print $11}'`
  if [ ! -f "/tmp/diskstats2" ]
  then
   disk_timw=0
   disk_timw2=0
   disk_timwv=0
  else
   disk_timw2=`grep "$df_device " /tmp/diskstats2 | awk '{print $11}'`
   the_diff=$(awk -v a=$disk_timw -v b=$disk_timw2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    disk_timwv=0
   else
    disk_timwv=$(awk -v a=$disk_timw -v b=$disk_timw2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$disk_timwv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$disk_timwv"
  fi
  disk_peno=`echo $line | awk '{print $12}'`
  if [ -z "$disk_peno" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$disk_peno"
  fi
  disk_ioti=`echo $line | awk '{print $13}'`
  if [ ! -f "/tmp/diskstats2" ]
  then
   disk_ioti=0
   disk_ioti2=0
   disk_iotiv=0
  else
   disk_ioti2=`grep "$df_device " /tmp/diskstats2 | awk '{print $13}'`
   the_diff=$(awk -v a=$disk_ioti -v b=$disk_ioti2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    disk_iotiv=0
   else
    disk_iotiv=$(awk -v a=$disk_ioti -v b=$disk_ioti2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$disk_iotiv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$disk_iotiv"
  fi
  disk_iotw=`echo $line | awk '{print $14}'`
  if [ ! -f "/tmp/diskstats2" ]
  then
   disk_iotw=0
   disk_iotw2=0
   disk_iotwv=0
  else
   disk_iotw2=`grep "$df_device " /tmp/diskstats2 | awk '{print $14}'`
   the_diff=$(awk -v a=$disk_iotw -v b=$disk_iotw2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    disk_iotwv=0
   else
    disk_iotwv=$(awk -v a=$disk_iotw -v b=$disk_iotw2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$disk_iotwv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$disk_iotwv"
  fi
  # Dimensions
  disk_name=`echo $line | awk '{print $3}'`
  if [ -z "$disk_name" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,\"$disk_name\""
   csv_valu="$csv_valu,\"$disk_type\""
   source $current_dir/lib/dims.sh

   if [ -f "/tmp/diskstats2" ]
   then
    echo $csv_valu
    csv_valu="\"$the_time\""
   fi
  fi
done </tmp/diskstats

echo "the_time=$the_time" >> /tmp/diskstats
mv /tmp/diskstats /tmp/diskstats2
