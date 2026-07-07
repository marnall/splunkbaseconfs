#!/bin/bash
current_dir="$(dirname "$0")"

cat /proc/net/dev | tail -n+3 > /tmp/interface

the_time=`date +%s.%3N`
csv_head='"_time"'
csv_valu="\"$the_time\""

csv_head="$csv_head,\"metric_name:interface.octets.rx\""
csv_head="$csv_head,\"metric_name:interface.packets.rx\""
csv_head="$csv_head,\"metric_name:interface.errors.rx\""
csv_head="$csv_head,\"metric_name:interface.dropped.rx\""
csv_head="$csv_head,\"metric_name:interface.octets.tx\""
csv_head="$csv_head,\"metric_name:interface.packets.tx\""
csv_head="$csv_head,\"metric_name:interface.errors.tx\""
csv_head="$csv_head,\"metric_name:interface.dropped.tx\""
csv_head="$csv_head,\"interface\""
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
  if_device=`echo $line | awk '{print $1}'`
  if [ -z "$if_device" ]
  then
   exit 1
  fi
  if_octr=`echo $line | awk '{print $2}'`
  if [ ! -f "/tmp/interface2" ]
  then
   if_octr=0
   if_octr2=0
   if_octrv=0
  else
   if_octr2=`grep "$if_device " /tmp/interface2 | awk '{print $2}'`
   the_time2=`grep the_time /tmp/interface2 | awk -F= '{print $2}'`
   the_diff=$(awk -v a=$if_octr -v b=$if_octr2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    if_octrv=0
   else
    if_octrv=$(awk -v a=$if_octr -v b=$if_octr2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$if_octrv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$if_octrv"
  fi
  if_pacr=`echo $line | awk '{print $3}'`
  if [ ! -f "/tmp/interface2" ]
  then
   if_pacr=0
   if_pacr2=0
   if_pacrv=0
  else
   if_pacr2=`grep "$if_device " /tmp/interface2 | awk '{print $3}'`
   the_diff=$(awk -v a=$if_pacr -v b=$if_pacr2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    if_pacrv=0
   else
    if_pacrv=$(awk -v a=$if_pacr -v b=$if_pacr2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$if_pacrv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$if_pacrv"
  fi
  if_errr=`echo $line | awk '{print $4}'`
  if [ ! -f "/tmp/interface2" ]
  then
   if_errr=0
   if_errr2=0
   if_errrv=0
  else
   if_errr2=`grep "$if_device " /tmp/interface2 | awk '{print $4}'`
   the_diff=$(awk -v a=$if_errr -v b=$if_errr2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    if_errrv=0
   else
    if_errrv=$(awk -v a=$if_errr -v b=$if_errr2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$if_errrv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$if_errrv"
  fi
  if_drpr=`echo $line | awk '{print $5}'`
  if [ ! -f "/tmp/interface2" ]
  then
   if_drpr=0
   if_drpr2=0
   if_drprv=0
  else
   if_drpr2=`grep "$if_device " /tmp/interface2 | awk '{print $5}'`
   the_diff=$(awk -v a=$if_drpr -v b=$if_drpr2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    if_drprv=0
   else
    if_drprv=$(awk -v a=$if_drpr -v b=$if_drpr2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$if_drprv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$if_drprv"
  fi
  if_octw=`echo $line | awk '{print $10}'`
  if [ ! -f "/tmp/interface2" ]
  then
   if_octw=0
   if_octw2=0
   if_octwv=0
  else
   if_octw2=`grep "$if_device " /tmp/interface2 | awk '{print $10}'`
   the_diff=$(awk -v a=$if_octw -v b=$if_octw2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    if_octwv=0
   else
    if_octwv=$(awk -v a=$if_octw -v b=$if_octw2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$if_octwv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$if_octwv"
  fi
  if_pacw=`echo $line | awk '{print $11}'`
  if [ ! -f "/tmp/interface2" ]
  then
   if_pacw=0
   if_pacw2=0
   if_pacwv=0
  else
   if_pacw2=`grep "$if_device " /tmp/interface2 | awk '{print $11}'`
   the_diff=$(awk -v a=$if_pacw -v b=$if_pacw2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    if_pacwv=0
   else
    if_pacwv=$(awk -v a=$if_pacw -v b=$if_pacw2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$if_pacwv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$if_pacwv"
  fi
  if_errw=`echo $line | awk '{print $12}'`
  if [ ! -f "/tmp/interface2" ]
  then
   if_errw=0
   if_errw2=0
   if_errwv=0
  else
   if_errw2=`grep "$if_device " /tmp/interface2 | awk '{print $12}'`
   the_diff=$(awk -v a=$if_errw -v b=$if_errw2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    if_errwv=0
   else
    if_errwv=$(awk -v a=$if_errw -v b=$if_errw2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$if_errwv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$if_errwv"
  fi
  if_drpw=`echo $line | awk '{print $13}'`
  if [ ! -f "/tmp/interface2" ]
  then
   if_drpw=0
   if_drpw2=0
   if_drpwv=0
  else
   if_drpw2=`grep "$if_device " /tmp/interface2 | awk '{print $13}'`
   the_diff=$(awk -v a=$if_drpw -v b=$if_drpw2 'BEGIN { print (a - b) }')
   if [[ $the_diff -eq 0 ]]
   then
    if_drpwv=0
   else
    if_drpwv=$(awk -v a=$if_drpw -v b=$if_drpw2 -v c=$the_time -v d=$the_time2 'BEGIN { print ((a - b) / (c - d)) }')
   fi
  fi
  if [ -z "$if_drpwv" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,$if_drpwv"
  fi
  # Dimensions
  interface=`echo $line | awk '{print $1}' | awk -F: '{print $1}'`
  if [ -z "$interface" ]
  then
   exit 1
  else
   csv_valu="$csv_valu,\"$interface\""
   source $current_dir/lib/dims.sh

   if [ -f "/tmp/interface2" ]
   then
    echo $csv_valu
    csv_valu="\"$the_time\""
   fi
  fi
done </tmp/interface

echo "the_time=$the_time" >> /tmp/interface
mv /tmp/interface /tmp/interface2
