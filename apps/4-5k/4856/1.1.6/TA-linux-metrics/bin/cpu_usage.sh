#!/bin/bash
current_dir="$(dirname "$0")"

the_time=`date +%s.%3N`
csv_head='"_time"'
csv_valu="\"$the_time\""

[[ "$(which top 2>/dev/null)" == "" ]] && echo "Error: cannot find 'top'" && exit 1
topOutput=`top -b -d1 -n2 | grep -w Cpu | grep -v grep | tail -1 | sed -e"s/%/ /g"`
IFS=":" read -ra NAMES <<< "$topOutput"
cpu_values=${NAMES[1]}
IFS="," read -ra NAMES2 <<< "$cpu_values"
cpu_values2=${NAMES2[@]}

for i in ${cpu_values2}
do
  key=`echo $i | grep -Po '\K([a-z]+)'`
  val=`echo $i | grep -Po '\K([\d\.]+)'`
  if [ -z "$key" ]
  then
   csv_valu="$csv_valu,$val"
  else
   if [ $key = "id" ]
   then
    key="idle"
   elif [ $key = "hi" ]
   then
    key="interrupt"
   elif [ $key = "ni" ]
   then
    key="nice"
   elif [ $key = "si" ]
   then
    key="softirq"
   elif [ $key = "st" ]
   then
    key="steal"
   elif [ $key = "sy" ]
   then
    key="system"
   elif [ $key = "us" ]
   then
    key="user"
   elif [ $key = "wa" ]
   then
    key="wait"
   fi
   csv_head="$csv_head,\"metric_name:cpu.$key\""
  fi
done

model=`grep "model name" /proc/cpuinfo | tail -1 | awk -F: '{print $2}' | cut -c 2-`
csv_head="$csv_head,\"model\""
csv_valu="$csv_valu,\"$model\""

source $current_dir/lib/dims.sh

echo $csv_head
echo $csv_valu
