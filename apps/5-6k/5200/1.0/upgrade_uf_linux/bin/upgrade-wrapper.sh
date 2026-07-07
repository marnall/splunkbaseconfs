#!/bin/bash

# set filename
UPGRADEFILE=splunkforwarder-8.0.4-767223ac207f-Linux-x86_64.tgz

# set desired version
NVER=8.0.4

# determine current version
CVER=`cat $SPLUNK_HOME/etc/splunk.version | grep VERSION | cut -d= -f2`

if [ "$NVER" != "$CVER" ]
then
        # get current path
        SCRIPT=`realpath $0`
        SCRIPTPATH=`dirname $SCRIPT`

	echo "Executing $SCRIPTPATH/upgrade.sh  $SPLUNK_HOME $SCRIPTPATH/.. $UPGRADEFILE $NVER " >&2
        (exec setsid sh $SCRIPTPATH/upgrade.sh $SPLUNK_HOME $SCRIPTPATH/.. $UPGRADEFILE $NVER &)
fi
