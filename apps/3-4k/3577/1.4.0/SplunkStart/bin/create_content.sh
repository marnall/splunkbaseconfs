#!/bin/sh

# usage (from SplunkStart/bin directory):
# create_content.sh <path to directory where local and metadata exist>

if [ $# -ne 1 ]
then
    echo "usage create_content.sh <path to dir where local and metadata exists>"
    exit
fi

if [ ! -d ../local ]
then
    mkdir ../local
fi


if [ ! -d ../local/data ]
then
    mkdir ../local/data
fi


if [ ! -d ../local/data/ui ]
then
    mkdir ../local/data/ui
fi

if [ ! -d  ../local/data/ui/views ]
then
    mkdir ../local/data/ui/views
fi

# If local is empty copy all default dashboards to local
if [ ! "$(ls -A ../local/data/ui/views)" ]
then
    cp $1/default/data/ui/views/*dashboard.xml ../local/data/ui/views/.
else
    for file in $1/default/data/ui/views/*dashboard.xml
    do
	b=$(basename $file)
	if [ ! -e ../local/data/ui/views/$b ]
	then
	    cp $file ../local/data/ui/views/.
	fi
    done
fi

# append your local macros.conf, savedsearches.conf and local.meta to app
echo "\n" >> ../local/macros.conf
cat $1/default/macros.conf >> ../local/macros.conf
echo "\n" >> ../local/savedsearches.conf
cat $1/default/savedsearches.conf >> ../local/savedsearches.conf
echo "\n" >> ../metadata/local.meta
cat $1/metadata/default.meta >> ../metadata/local.meta

# Copy files for advance macro and title replacement, if they exist.

if   ls $1/src/macros/macros*.txt 1> /dev/null 2>&1
then
    cp $1/src/macros/macros*.txt ../src/macros/.
fi

if   ls $1/src/titles/titles*.csv 1> /dev/null 2>&1
then
    cp $1/src/titles/titles*.csv ../src/titles/.
fi

## Copy lookup files, if they exist. 
if   ls $1/lookups/*.csv 1> /dev/null 2>&1
then
    cp $1/lookups/*.csv ../lookups/.
fi