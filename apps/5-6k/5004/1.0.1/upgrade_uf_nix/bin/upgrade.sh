#!/bin/bash
# get splunk path from argument
SPLUNK_HOME=$1

# get app path from argument
SPLUNK_APP=$2

# get tarball filename from argument
NFILE=$3

# get desired version from argument
NVER=$4

# determine current version
CVER=`/usr/bin/cat $SPLUNK_HOME/etc/splunk.version | /usr/bin/grep VERSION | /usr/bin/cut -d= -f2`

if [[ "$NVER" > "$CVER" ]]
then
	/usr/bin/logger "Upgrading Splunk to $NVER."
	$SPLUNK_HOME/bin/splunk stop
	/usr/bin/logger "Extracting Splunk: tar --totals -xzf $SPLUNK_APP/static/$NFILE -C $SPLUNK_HOME/.. "
	/usr/bin/tar --totals -xzf $SPLUNK_APP/static/$NFILE -C $SPLUNK_HOME/.. 2>&1 | /usr/bin/logger &
	/usr/bin/wait %1
	/usr/bin/sleep 10
	CVER=`/usr/bin/cat $SPLUNK_HOME/etc/splunk.version | /usr/bin/grep VERSION | /usr/bin/cut -d= -f2`
	/usr/bin/logger "Starting Splunk $CVER for first time."
	$SPLUNK_HOME/bin/splunk start --accept-license --answer-yes --no-prompt 2>&1 | logger &
	/usr/bin/wait %1
	/usr/bin/sleep 20
	/usr/bin/logger "Started Splunk $CVER."
fi

# if installed version now newer, then delete tgz file
CVER=`/usr/bin/cat $SPLUNK_HOME/etc/splunk.version | /usr/bin/grep VERSION | /usr/bin/cut -d= -f2`
if [[ "$NVER" -le "$CVER" ]]
then
	/usr/bin/cat /dev/null $SPLUNK_APP/static/$NFILE
fi
