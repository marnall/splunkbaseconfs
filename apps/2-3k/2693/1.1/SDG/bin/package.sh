#!/bin/bash
CONFS=();
for entry in ../local/*.conf
do
	myPath=${entry##*/}
	filename=${myPath%.*conf}
	if [ -f "$entry" ];then
		CONFS=("${CONFS[@]}" "$filename")
	fi
done
echo ${CONFS[@]}
for conf in ${CONFS[@]}; do
	echo "Writing to $conf.conf"
	/opt/splunk/bin/splunk cmd btool $conf list --app=$1 > ./mergedConfs/$conf.conf
done
echo "Files written into mergedConfs. Copy where desired!"
