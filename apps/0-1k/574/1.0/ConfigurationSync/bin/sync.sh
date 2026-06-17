#!/bin/sh

date

START=`date +%s`

PWD=`dirname $0`
DEST_SERVER=`grep '^DEST_SERVER' $PWD/../local/dest.conf | cut -d '=' -f 2`

SPLUNKWEB_RUNNING=`$SPLUNK_HOME/bin/splunk status | grep "splunkweb is running"`
echo $SPLUNKWEB_RUNNING

#-n means string is not empty
if test -n "$SPLUNKWEB_RUNNING" ; then
  echo "splunkweb is running. Marking myself hot."
  touch $SPLUNK_HOME/etc/apps/ConfigurationSync/bin/isHot

  REMOTE_IS_HOT=`ssh $DEST_SERVER 'test -f $SPLUNK_HOME/etc/apps/ConfigurationSync/bin/isHot && echo exists'`

  #-z means string is empty
  if test -z $REMOTE_IS_HOT ; then
    TAR_SRC=`cat $SPLUNK_HOME/etc/apps/ConfigurationSync/bin/PathsToCopy.txt | tr '\n' ' '`

    echo copying $TAR_SRC from $SPLUNK_HOME to $DEST_SERVER
    tar -cf - $TAR_SRC | ssh $DEST_SERVER tar -C / -xvf -

    for SYNC_SRC in `cat $SPLUNK_HOME/etc/apps/ConfigurationSync/bin/PathsToRsync.txt`; do
      SYNC_DEST=`echo $SYNC_SRC | sed -e 's#[^/]\+$##g'`
      echo syncing $SYNC_SRC to $DEST_SERVER:$SYNC_DEST
      rsync -av --delete $SYNC_SRC $DEST_SERVER:$SYNC_DEST
    done
  else
    echo "isHot is in place on $DEST_SERVER. Not going to run."
  fi
  
else
  echo "isHot not found or splunkweb not running. Not going to run."
fi

echo runtime=$((`date +%s` - $START))
echo ' '


