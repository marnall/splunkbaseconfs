#!/bin/bash

# set log file path

LOG_FILE=$SPLUNK_HOME/upgrade.log
ERROR_LOG=$SPLUNK_HOME/upgrade_stderr.log

# write stdout & stderr to the logfile

exec 1>>${LOG_FILE}
exec 2>>${ERROR_LOG}
exec 2>&1>>${LOG_FILE}

# get splunk path from argument
SPLUNK_HOME=$1

# get app path from argument
SPLUNK_APP=$2

# backup existing splunk into below path
BACKUP_LOC=/tmp/

# get tarball filename from argument
NFILE=$3

# get desired version from argument
NVER=$4

# determine current version
CVER=`cat $SPLUNK_HOME/etc/splunk.version | grep VERSION | cut -d= -f2` | tee -a $LOG_FILE &

if [[ "$NVER" > "$CVER" ]]
then
	echo -e "Upgrading Splunk to $NVER."
	$SPLUNK_HOME/bin/splunk stop
        sleep 300
        echo -e "Backing up existing Splunk: tar -czPf $BACKUP_LOC/$(hostname).tar.gz $SPLUNK_HOME/.. "
        tar czPf $BACKUP_LOC/$(hostname).tar.gz $SPLUNK_HOME/..  2>&1 | tee -a $LOG_FILE &
        sleep 420
	echo -e "Extracting Splunk: tar --totals -xzf $SPLUNK_APP/static/$NFILE -C $SPLUNK_HOME/.. "
	tar --totals -xzf $SPLUNK_APP/static/$NFILE -C $SPLUNK_HOME/.. 2>&1 | tee -a $LOG_FILE &
	sleep 120
	CVER=`cat $SPLUNK_HOME/etc/splunk.version | grep VERSION | cut -d= -f2`
	echo -e "Starting Splunk $CVER for first time."
	$SPLUNK_HOME/bin/splunk start --accept-license --answer-yes --no-prompt 2>&1 | tee -a $LOG_FILE &
	sleep 20
	echo -e "Started Splunk $CVER."
fi
