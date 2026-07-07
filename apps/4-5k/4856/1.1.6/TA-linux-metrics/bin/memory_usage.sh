#!/bin/bash
current_dir="$(dirname "$0")"

cat /proc/meminfo > /tmp/meminfo

the_time=`date +%s.%3N`
csv_head='"_time"'
csv_valu="\"$the_time\""

mem_total=`grep -i 'MemTotal' /tmp/meminfo | awk '{print $2}'`
if [ -z "$mem_total" ]
then
 mem_total=0.0
fi
mem_free=`grep -i 'MemFree' /tmp/meminfo | awk '{print $2}'`
if [ -z "$mem_free" ]
then
 mem_free2=0.0
 csv_head="$csv_head,\"metric_name:memory.free\""
 csv_valu="$csv_valu,$mem_free2"
else
 mem_free2=$(awk -v f=$mem_free -v t=$mem_total 'BEGIN { print ((f / t) * 100) }')
 csv_head="$csv_head,\"metric_name:memory.free\""
 csv_valu="$csv_valu,$mem_free2"
fi
mem_buffered=`grep -i 'Buffers' /tmp/meminfo | awk '{print $2}'`
if [ -z "$mem_buffered" ]
then
 mem_buffered2=0.0
 csv_head="$csv_head,\"metric_name:memory.buffered\""
 csv_valu="$csv_valu,$mem_buffered2"
else
 mem_buffered2=$(awk -v b=$mem_buffered -v t=$mem_total 'BEGIN { print ((b / t) * 100) }')
 csv_head="$csv_head,\"metric_name:memory.buffered\""
 csv_valu="$csv_valu,$mem_buffered2"
fi
mem_cached=`grep -w 'Cached' /tmp/meminfo | awk '{print $2}'`
if [ -z "$mem_cached" ]
then
 mem_cached2=0.0
 csv_head="$csv_head,\"metric_name:memory.cached\""
 csv_valu="$csv_valu,$mem_cached2"
else
 mem_cached2=$(awk -v c=$mem_cached -v t=$mem_total 'BEGIN { print ((c / t) * 100) }')
 csv_head="$csv_head,\"metric_name:memory.cached\""
 csv_valu="$csv_valu,$mem_cached2"
fi
mem_slab=`grep -i 'Reclaimable' /tmp/meminfo | awk '{print $2}'`
if [ -z "$mem_slab" ]
then
 mem_slab2=0.0
 csv_head="$csv_head,\"metric_name:memory.slab_recl\""
 csv_valu="$csv_valu,$mem_slab2"
else
 mem_slab2=$(awk -v s=$mem_slab -v t=$mem_total 'BEGIN { print ((s / t) * 100) }')
 csv_head="$csv_head,\"metric_name:memory.slab_recl\""
 csv_valu="$csv_valu,$mem_slab2"
fi
mem_slabu=`grep -i 'SUnreclaim' /tmp/meminfo | awk '{print $2}'`
if [ -z "$mem_slabu" ]
then
 mem_slabu2=0.0
 csv_head="$csv_head,\"metric_name:memory.slab_unrecl\""
 csv_valu="$csv_valu,$mem_slabu2"
else
 mem_slabu2=$(awk -v u=$mem_slabu -v t=$mem_total 'BEGIN { print ((u / t) * 100) }')
 csv_head="$csv_head,\"metric_name:memory.slab_unrecl\""
 csv_valu="$csv_valu,$mem_slabu2"
fi
mem_used=`grep -i 'MemFree' /tmp/meminfo | awk '{print $2}'`
if [ -z "$mem_used" ]
then
 mem_used2=0.0
 csv_head="$csv_head,\"metric_name:memory.used\""
 csv_valu="$csv_valu,$mem_used2"
else
 #mem_used3=$(awk -v f=$mem_free -v b=$mem_buffered -v c=$mem_cached -v t=$mem_total -v s=$mem_slab 'BEGIN { print ( t - f - b - c - s) }')
 mem_used3=$(awk -v f=$mem_free -v b=$mem_buffered -v c=$mem_cached -v t=$mem_total 'BEGIN { print ( t - f - b - c ) }')
 mem_used2=$(awk -v u=$mem_used3 -v t=$mem_total 'BEGIN { print ((u / t) * 100) }')
 csv_head="$csv_head,\"metric_name:memory.used\""
 csv_valu="$csv_valu,$mem_used2"
fi

source $current_dir/lib/dims.sh

echo $csv_head
echo $csv_valu

rm -f /tmp/meminfo
