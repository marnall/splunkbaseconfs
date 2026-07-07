#!/bin/sh

# set -x

# Program name: nmonparser.sh
# Purpose - Frontal script to nmonparser, will launch Python or Perl script depending on interpreter availability
#				See nmonparser | nmonparser.pl
# Author - Guilhem Marchand

# Version 2.0.1

# For AIX / Linux / Solaris

#################################################
## 	Your Customizations Go Here            ##
#################################################

# format date output to strftime dd/mm/YYYY HH:MM:SS
log_date () {
    date "+%d-%m-%Y %H:%M:%S"
}

# Set host
HOST=`hostname`

# Which type of OS are we running
UNAME=`uname`

if [ -z "${SPLUNK_HOME}" ]; then
	echo "`log_date`, ERROR, SPLUNK_HOME variable is not defined"
	exit 1
fi

# Set tmp directory
APP_VAR=${SPLUNK_HOME}/var/log/metricator

# Verify it exists
if [ ! -d ${APP_VAR} ]; then
    mkdir -p ${APP_VAR}
	exit 1
fi

# silently remove tmp file (testing exists before rm seems to cause trouble on some old OS)
rm -f ${APP_VAR}/nmonparser.temp.*

# Set nmon_temp
nmon_temp=${APP_VAR}/nmonparser.temp.$$

# APP path discovery
if [ -d "$SPLUNK_HOME/etc/apps/TA-metricator-for-nmon" ]; then
        APP=$SPLUNK_HOME/etc/apps/TA-metricator-for-nmon

elif [ -d "$SPLUNK_HOME/etc/peer-apps/TA-metricator-for-nmon" ];then
        APP=$SPLUNK_HOME/etc/peer-apps/TA-metricator-for-nmon

else
        echo "`log_date`, ${HOST} ERROR, the APP directory could not be defined, is the TA-metricator-for-nmon installed ?"
        exit 1
fi

reformat_default_nmon_conf () {

    # Retrieve category from first arg
    nmon_conf=$1

    # This function removes Splunk-added stanzas (like [default], [nmon], etc.) and normalizes
    # variable assignments by removing spaces around = signs to make the file sourceable as a shell script

    case $UNAME in
    "Linux")
            # Remove all stanza lines (lines matching pattern ^\[.*\]$)
            sed -i '/^\[.*\]$/d' ${nmon_conf}
            # Normalize variable assignments: remove spaces around = sign
            sed -i 's/ = /=/g' ${nmon_conf}
            sed -i 's/ =/=g' ${nmon_conf}
            sed -i 's/= /=/g' ${nmon_conf}
    ;;
    *)
            # Remove all stanza lines and normalize variable assignments
            cat ${nmon_conf} | sed '/^\[.*\]$/d' | sed 's/ = /=/g' | sed 's/ =/=g' | sed 's/= /=/g' > /tmp/nmonparser.tmp.$$
            mv /tmp/nmonparser.tmp.$$ ${nmon_conf}
    ;;
    esac

}

# source default nmon.conf
if [ -f $APP/default/nmon.conf ]; then
    # Check for any Splunk stanza pattern and reformat if needed
    grep '^\[.*\]$' $APP/default/nmon.conf >/dev/null
    if [ $? -eq 0 ]; then
        reformat_default_nmon_conf $APP/default/nmon.conf
        . $APP/default/nmon.conf
    else
        . $APP/default/nmon.conf
    fi
fi

# source local nmon.conf, if any

# Search for a local nmon.conf file located in $SPLUNK_HOME/etc/apps/TA-metricator-for-nmon/local
if [ -f $APP/local/nmon.conf ]; then
    # Check for any Splunk stanza pattern and reformat if needed
    grep '^\[.*\]$' $APP/local/nmon.conf >/dev/null
    if [ $? -eq 0 ]; then
        reformat_default_nmon_conf $APP/local/nmon.conf
        . $APP/local/nmon.conf
    else
        . $APP/local/nmon.conf
    fi
fi

# On a per server basis, you can also set in /etc/nmon.conf
if [ -f /etc/nmon.conf ]; then
    # Check for any Splunk stanza pattern and reformat if needed
    grep '^\[.*\]$' /etc/nmon.conf >/dev/null
    if [ $? -eq 0 ]; then
        reformat_default_nmon_conf /etc/nmon.conf
        . /etc/nmon.conf
    else
        . /etc/nmon.conf
    fi
fi

# Manage FQDN option
echo $nmonparser_options | grep '\-\-use_fqdn' >/dev/null
if [ $? -eq 0 ]; then
    # Only relevant for Linux OS
    case $UNAME in
    Linux)
        HOST=`hostname -f` ;;
    AIX)
        HOST=`hostname` ;;
    SunOS)
        HOST=`hostname` ;;
    esac
else
    HOST=`hostname`
fi

# Manage host override option based on Splunk hostname defined
case $override_sys_hostname in
"1")
    # Retrieve the Splunk host value
    HOST=`cat $SPLUNK_HOME/etc/system/local/inputs.conf | grep '^host =' | awk -F\= '{print $2}' | sed 's/ //g'`
;;
esac

#
# Interpreter choice
#

PYTHON=0
PYTHON2=0
PYTHON3=0
PERL=0
# Set the default interpreter
INTERPRETER="python"

# Get the version for both worlds
PYTHON2=`which python 2>&1`
PYTHON3=`which python3 2>&1`
PERL=`which perl 2>&1`

# Handle Python
PYTHON_available="false"
case $PYTHON3 in
*python*)
    PYTHON_available="true"
    INTERPRETER="python3" ;;
*)
    case $PYTHON2 in
    *python*)
        PYTHON_available="true"
        INTERPRETER="python" ;;
    esac
;;
esac

# Handle Perl
case $PERL in
*perl*)
   PERL_available="true"
   ;;
*)
   PERL_available="false"
   ;;
esac

case `uname` in

# AIX priority is Perl
"AIX")
     case $PERL_available in
     "true")
           INTERPRETER="perl" ;;
     "false")
           INTERPRETER="$INTERPRETER" ;;
 esac
;;

# Other OS, priority is Python
*)
     case $PYTHON_available in
     "true")
           INTERPRETER="$INTERPRETER" ;;
     "false")
           INTERPRETER="perl" ;;
     esac
;;
esac

####################################################################
#############		Main Program 			############
####################################################################

# Store arguments sent to script
userargs=$@

# Store stdin
while read line ; do
	echo "$line" >> ${nmon_temp}
done

# Start the parser
case ${INTERPRETER} in

"python"|"python3")
    cat ${nmon_temp} | ${SPLUNK_HOME}/bin/splunk cmd $INTERPRETER ${APP}/bin/nmonparser.py ${userargs} ;;

"perl")
	cat ${nmon_temp} | ${SPLUNK_HOME}/bin/splunk cmd ${APP}/bin/nmonparser.pl ${userargs} ;;

esac

# Remove temp
rm -f ${nmon_temp}

exit 0
