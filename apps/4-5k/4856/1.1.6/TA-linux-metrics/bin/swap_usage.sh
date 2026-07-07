#!/bin/bash
current_dir="$(dirname "$0")"

cat /proc/meminfo > /tmp/swpinfo

the_time=`date +%s.%3N`
csv_head='"_time"'
csv_valu="\"$the_time\""

swp_total=`grep -i 'SwapTotal' /tmp/swpinfo | awk '{print $2}'`
if [ -z "$swp_total" ]
then
 swp_total=0.0
fi
swp_cached=`grep 'SwapCached' /tmp/swpinfo | awk '{print $2}'`
if [ -z "$swp_cached" ]
then
 swp_cached2=0.0
 csv_head="$csv_head,\"metric_name:swap.cached\""
 csv_valu="$csv_valu,$swp_cached2"
elif [[ $swp_cached -eq 0 ]]
then
 swp_cached2=0.0
 csv_head="$csv_head,\"metric_name:swap.cached\""
 csv_valu="$csv_valu,$swp_cached2"
else
 swp_cached2=$(awk -v s=$swp_cached -v t=$swp_total 'BEGIN { print ((s / t) * 100) }')
 csv_head="$csv_head,\"metric_name:swap.cached\""
 csv_valu="$csv_valu,$swp_cached2"
fi
swp_free=`grep -i 'SwapFree' /tmp/swpinfo | awk '{print $2}'`
if [ -z "$swp_free" ]
then
 swp_free2=0.0
 csv_head="$csv_head,\"metric_name:swap.free\""
 csv_valu="$csv_valu,$swp_free2"
elif [[ $swp_free -eq 0 ]]
then
 swp_free2=0.0
 csv_head="$csv_head,\"metric_name:swap.free\""
 csv_valu="$csv_valu,$swp_free2"
else
 swp_free2=$(awk -v f=$swp_free -v t=$swp_total 'BEGIN { print ((f / t) * 100) }')
 csv_head="$csv_head,\"metric_name:swap.free\""
 csv_valu="$csv_valu,$swp_free2"
fi
swp_used=`grep -i 'SwapFree' /tmp/swpinfo | awk '{print $2}'`
if [ -z "$swp_used" ]
then
 swp_used2=0.0
 csv_head="$csv_head,\"metric_name:swap.used\""
 csv_valu="$csv_valu,$swp_used2"
elif [[ $swp_used -eq 0 ]]
then
 swp_used2=0.0
 csv_head="$csv_head,\"metric_name:swap.used\""
 csv_valu="$csv_valu,$swp_used2"
else
 swp_used3=$(awk -v f=$swp_free -v c=$swp_cached -v t=$swp_total 'BEGIN { print ( t - f - c ) }')
 swp_used2=$(awk -v u=$swp_used3 -v t=$swp_total 'BEGIN { print ((u / t) * 100) }')
 csv_head="$csv_head,\"metric_name:swap.used\""
 csv_valu="$csv_valu,$swp_used2"
fi

source $current_dir/lib/dims.sh

echo $csv_head
echo $csv_valu

rm -f /tmp/swpinfo
