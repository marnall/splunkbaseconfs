#!/bin/sh

# check read/execute perms for supplied dir, file or dir/file and identify first level where permissions are blocked
# the primary purpose of this script is to identify permissions issues in order to determine why a Splunk agent cannot read a log 
# this script could potentially be used to check if logs exist or audit when log ownership or permissions are changed or if a log file is added or deleted
#
# this script will read inputs from check-log-permissions.conf 
# it is recommened to copy TA-check-log-permissions/default/check-log-permissions.conf to TA-check-log-permissions/local/check-log-permissions.conf
# and then make your edits
# TA-check-log-permissions/default/inputs.conf controls frequency of execution and what index events will be sent to
#
# rob@jordan2000.com
# ver 1.0.9
# created 12/22/2015
# last updated 4/3/2016

# uncomment/comment line below to turn debug on/off
#set -x

INPUT=$1

ValidateInput ()
{

if [ "$SPLUNK_HOME" = "" ]
then
	echo "WARNING: SPLUNK_HOME not set."
	echo "You may need to set SPLUNK_HOME manualy if testing this script from the command line."
	echo "EXAMPLE: export SPLUNK_HOME=/opt/splunk"
	echo "NOTE: SPLUNK_HOME location will vary based on your installation."
	exit 1
fi

# check input for absolute path - if relative path, convert to absolute path
INPUT_CHECK=`echo $INPUT|grep "/"|wc -l`
if [ $INPUT_CHECK -eq 0 ]
then
	printf "Reformating input...\n"
	OLD_INPUT="$INPUT"
	NEW_INPUT="$PWD/$INPUT"
	INPUT="$NEW_INPUT"
fi
}

PrintRecord ()
{
printf "DATE=\"$DATE\" "
printf "SERVER=\"$SERVER\" "
printf "INPUT=\"$INPUT\" "
printf "READ_STATUS=\"$READ_STATUS\" "
printf "RESOURCE_TYPE=\"$RESOURCE_TYPE\" "
printf "RESOURCE_PATH=\"$RESOURCE_PATH\" "
printf "RESOURCE=\"$RESOURCE\" "
printf "RESOURCE_DETAIL=\"$RESOURCE_DETAIL\" "
printf "FORWARDER_ID=\"$FORWARDER_ID\" "
printf "FORWARDER_ID_DETAIL=\"$FORWARDER_ID_DETAIL\" "
printf "\n"
}

DirectoryTest ()
{
RESOURCE_TYPE=directory
if ! test -x "$RESOURCE_PATH"
then
	READ_STATUS="fail"
else
	READ_STATUS="success"
fi
}

FileTest ()
{
RESOURCE_TYPE=file
if ! test -r "$RESOURCE_PATH"
then
	READ_STATUS="fail"
else
	READ_STATUS="success"
fi
}

GetForwarderInfo ()
{
SERVER=`uname -nsr`
FORWARDER_ID=`id|awk '{print $1}' | head -1`
FORWARDER_ID_DETAIL=`id | head -1`
}

CheckForReadFailure ()
{
	DATE=`date`

	# root directory check
	RESOURCE_PATH="/"
	RESOURCE="/"
	RESOURCE_PATH_OWNER=`ls -ldL "$RESOURCE_PATH" 2>/dev/null | awk '{print $3}'`
	RESOURCE_DETAIL=`ls -ldL "$RESOURCE_PATH" 2>/dev/null`
	
	if [ "$RESOURCE_DETAIL" = "" ]
	then
		RESOURCE_DETAIL="unavailable or does not exist"
	fi

	DirectoryTest
	PrintRecord
	RESOURCE_PATH=""

	# parse path and step through directory levels
	# set field separator to "/"
        IFS="/"
        for RESOURCE in $INPUT
        do
                if [ "$RESOURCE" != "" ]
                then
                        RESOURCE_PATH="$RESOURCE_PATH/$RESOURCE"
                        RESOURCE_PATH_OWNER=`ls -ldL "$RESOURCE_PATH" 2>/dev/null | awk '{print $3}'`

			# dtermine if directory, file or unknown
                        if test -d "$RESOURCE_PATH"
                        then
				DirectoryTest
                        else
				if test -f "$RESOURCE_PATH"
				then
					FileTest
				else
					RESOURCE_TYPE=unknown
					READ_STATUS="fail"
				fi
                        fi

			RESOURCE_DETAIL=`ls -ldL "$RESOURCE_PATH" 2>/dev/null`
			if [ "$RESOURCE_DETAIL" = "" ]
			then
				RESOURCE_DETAIL="unavailable or does not exist"
			fi
			
			PrintRecord
                fi
        done

	# return field separator to default
        IFS=""
}


################################################################################
# MAIN
################################################################################

ValidateInput

# read records from input file while ignoring blank or records with a # sign
# determine if we should use check-log-permissions.conf in /default or /local directory

if test -r $SPLUNK_HOME/etc/apps/TA-check-log-permissions/local/check-log-permissions.conf
then
	CONFIG_FILE=$SPLUNK_HOME/etc/apps/TA-check-log-permissions/local/check-log-permissions.conf
else
	CONFIG_FILE=$SPLUNK_HOME/etc/apps/TA-check-log-permissions/default/check-log-permissions.conf
fi

cat  $CONFIG_FILE | grep -v "#" | grep -v "^$" | while read RECORD
do
        MONITOR_COUNT=`ls -d $RECORD 2>/dev/null | wc -l`
        if [ $MONITOR_COUNT -gt 0 ] 
        then
                ls -d $RECORD | while read INPUT
                do

			ValidateInput
			GetForwarderInfo
			CheckForReadFailure

		done
        else
			# no monitor returned - instead check permissions of input supplied in config file
			INPUT=$RECORD
                        ValidateInput
			GetForwarderInfo
                        CheckForReadFailure
        fi
done

