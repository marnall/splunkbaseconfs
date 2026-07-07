#!/bin/bash

# set filename
UPGRADEFILE=splunkforwarder-8.0.4-767223ac207f-Linux-x86_64.tgz

# set desired version
UPGRADEVER=8.0.4

if [ "$(/usr/bin/uname -s)" = "Linux" ] && [ "$(/usr/bin/uname -m)" = "x86_64" ] && [[ `$SPLUNK_HOME/bin/splunk version | grep "Universal Forwarder"` ]] ; then
        # get current path
        SCRIPT=`/usr/bin/realpath $0`
        SCRIPTPATH=`/usr/bin/dirname $SCRIPT`

	echo "Executing $SCRIPTPATH/upgrade.sh  $SPLUNK_HOME $SCRIPTPATH/.. $UPGRADEFILE $UPGRADEVER " >&2
        (exec /usr/bin/setsid /usr/bin/sh $SCRIPTPATH/upgrade.sh $SPLUNK_HOME $SCRIPTPATH/.. $UPGRADEFILE $UPGRADEVER &)
fi
