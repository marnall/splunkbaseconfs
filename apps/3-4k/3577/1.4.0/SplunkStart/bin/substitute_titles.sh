#!/bin/sh

# usage (from SplunkStart directory):
# bin/substitute_titles.sh <titles.csv file> that has 2 columns

if [ $# -ne 1 ]
then
    echo "usage substitute_titles.sh <titles.csv file> that has 2 columns"
    exit
fi

if [ ! -d local ]
then
    mkdir local
fi


if [ ! -d local/data ]
then
    mkdir local/data
fi

if [ ! -d local/data/ui ]
then
    mkdir local/data/ui
fi

if [ ! -d local/data/ui/views ]
then
    mkdir local/data/ui/views
fi

# If local is empty copy all default dashboards to local
if [ ! "$(ls -A local/data/ui/views)" ]
then
    cp default/data/ui/views/*dashboard.xml local/data/ui/views/.
else
    for file in default/data/ui/views/*dashboard.xml
    do
	b=$(basename $file)
	if [ ! -e local/data/ui/views/$b ]
	then
	    cp $file local/data/ui/views/.
	fi
    done
fi

count=0
for file in local/data/ui/views/*dashboard.xml
do
    bin/substitute_titles.py $1 $file
    count=`expr ${count} + 1`
    echo "Possibly updated " $file
done

echo "Examined " $count " files in /data/ui/views directory"





