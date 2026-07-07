#!/bin/bash

# chmod a+x <this file> before deployment

# script fetches the hostname from the environment
# converts it to lowercase and truncates any FQDN
# inserts it into etc/system/local server.conf and inputs.conf if necessary
# restarts splunk
# tested on RHEL7 and Solaris11

# set localization from international (cuz old Gnu on Solaris)
LC_ALL="C"

if [ "$SPLUNK_HOME"  = "" ]; then
 SPLUNK_HOME="/opt/splunkforwarder"
fi

SCRIPT=`/usr/bin/realpath $0`
SCRIPTPATH=`/usr/bin/dirname $SCRIPT`
SERVERCONF="$SPLUNK_HOME/etc/system/local/server.conf"
INPUTSCONF="$SPLUNK_HOME/etc/system/local/inputs.conf"
OS=`/usr/bin/uname -s`
REBOOTFLAG=false

CONFCOMMENT="#"$(/usr/bin/date +"%Y-%m-%d %T")" changed by rectify_hostname"

# only run on UFs
if ![[ `$SPLUNK_HOME/bin/splunk version | grep "Universal Forwarder"` ]] ; then
 exit
fi

# for Solaris, need Gnu tools
if [ "$OS" = "SunOS" ]; then
 shopt -s expand_aliases
 /usr/bin/alias grep='/usr/gnu/bin/grep'
 /usr/bin/alias sed='/usr/gnu/bin/sed'
# for AIX, need Gnu tools (untested)
elif [ "$OS" = "AIX" ]; then
 shopt -s expand_aliases
 /usr/bin/alias grep='/usr/linux/bin/grep'
 /usr/bin/alias sed='/usr/linux/bin/sed'
elif [ "$OS" = "Linux" ]; then
 shopt -s expand_aliases
 /usr/bin/alias grep='/usr/bin/grep'
 /usr/bin/alias sed='/usr/bin/sed'
fi

# get hostname from OS, abort if too long or short
LOWERSHORTHOSTNAME=$(sed -r 's/^([^\.]+).*?$/\L\1/' <<< "$(/usr/bin/uname -n)")
if [ "$(/usr/bin/expr length $LOWERSHORTHOSTNAME)" -gt 20 ] || [ "$(/usr/bin/expr length $LOWERSHORTHOSTNAME)"  -lt 3 ] ; then
 exit
fi


# two checks, in case serverName is set twice
if ((! (grep -E -q '^serverName = '"$LOWERSHORTHOSTNAME"'$' $SERVERCONF)) || (grep -E -q '^\s*?serverName\s*?=\s*?\$?.*?[A-Z\.].*?$' $SERVERCONF)) ; then
 sed -i -r 's/^(\s*?serverName\s*?=.*?)$/'"$CONFCOMMENT"'\n#\1\nserverName = '"$LOWERSHORTHOSTNAME"'/g' $SERVERCONF
 if (grep -E -q '^serverName = '"$LOWERSHORTHOSTNAME"'$' $SERVERCONF) ; then
  REBOOTFLAG=true
 fi
fi

if ((! (grep -E -q '^host = '"$LOWERSHORTHOSTNAME"'$' $INPUTSCONF)) || (grep -E -q '^\s*?host\s*?=\s*?\$?.*?[A-Z\.].*?$' $INPUTSCONF)) ; then
 sed -i -r 's/^(\s*?host\s*?=.*?)$/'"$CONFCOMMENT"'\n#\1\nhost = '"$LOWERSHORTHOSTNAME"'/g' $INPUTSCONF
 if (grep -E -q '^host = '"$LOWERSHORTHOSTNAME"'$' $INPUTSCONF) ; then
  REBOOTFLAG=true
 fi
fi


# delete GUID if anything changed.
if $REBOOTFLAG ; then
  /usr/bin/rm -f $SPLUNK_HOME/etc/instance.cfg
fi


if $REBOOTFLAG && [ "$OS" = "Linux" ]; then

  (exec /usr/bin/setsid /usr/bin/sh $SCRIPTPATH/restart_splunk.sh $SPLUNK_HOME &)

elif $REBOOTFLAG && [ "$OS" = "SunOS" ]; then

  (exec sh $SCRIPTPATH/restart_splunk.sh $SPLUNK_HOME &)

fi
