#!/bin/sh

# set -x

# Program name: metricator_cleaner.sh
# Purpose - Frontal script to metricator_cleaner.py and metricator_cleaner.pl, will launch Python or Perl script depending on interpreter availability
#				See metricator_cleaner.py | metricator_cleaner.pl
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

# hostname
HOST=`hostname`

# Which type of OS are we running
UNAME=`uname`

if [ -z "${SPLUNK_HOME}" ]; then
	echo "`log_date`, ${HOST} ERROR, SPLUNK_HOME variable is not defined"
	exit 1
fi

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
            cat ${nmon_conf} | sed '/^\[.*\]$/d' | sed 's/ = /=/g' | sed 's/ =/=g' | sed 's/= /=/g' > /tmp/metricator_cleaner.tmp.$$
            mv /tmp/metricator_cleaner.tmp.$$ ${nmon_conf}
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

# POSIX process run time in seconds (for Solaris only)
P_RUNTIME () {
 t=`LC_ALL=POSIX ps -o etime= -p $1 | awk '{print $1}'`
 d=0 h=0
 case $t in *-*) d=$((0 + ${t%%-*})); t=${t#*-};; esac
 case $t in *:*:*) h=$((0 + ${t%%:*})); t=${t#*:};; esac
 s=$((10#$d*86400 + 10#$h*3600 + 10#${t%%:*}*60 + 10#${t#*:}))
 echo $s
}

####################################################################
#############		Main Program 			############
####################################################################

# Store arguments sent to script
userargs=$@

###### Maintenance tasks ######

#
# Maintenance task1
#

# Maintenance task 1: verify if we have nmon processes running over the allowed period
# This issue seems to happen sometimes specially on AIX servers

# If an nmon process has not been terminated after its grace period, the process will be killed

# get the allowed runtime in seconds for an nmon process according to the configuration
# and add a 10 minute grace period

case `uname` in

"AIX"|"Linux"|"SunOS")

    echo "`log_date`, ${HOST} INFO, starting maintenance task 1: verify nmon processes running over expected time period"

    endtime=0

    case ${mode_fifo} in
    "1")
        endtime=`expr ${fifo_interval} \* ${fifo_snapshot}` ;;
    *)
        endtime=`expr ${interval} \* ${snapshot}` ;;
    esac

    endtime=`expr ${endtime} + 600`

    # get the list of running processes
    case $UNAME in
    "AIX"|"Linux")
        oldPidList=`ps -eo user,pid,command,etime,args | grep "nmon" | grep "splunk" | grep "var/log/metricator" | grep -v metricator_reader | grep -v grep | awk '{ print $2 }'`
        ps -eo user,pid,command,etime,args | grep "nmon" | grep "splunk" | grep "var/log/metricator" | grep -v metricator_reader | grep -v grep >/dev/null ;;
    "SunOS")
        oldPidList=`ps auxwww | grep "sadc" | grep "splunk" | grep "var/log/metricator" | grep -v metricator_reader | grep -v grep | awk '{ print $2 }'`
        ps auxwww | grep "sadc" | grep "splunk" | grep "var/log/metricator" | grep -v metricator_reader | grep -v grep >/dev/null ;;
    esac

    if [ $? -eq 0 ]; then

        for pid in $oldPidList; do

            pid_runtime=0
            # only run the process is running
            if [ -d /proc/${pid} ]; then
                # get the process runtime in seconds

                case $UNAME in
                "AIX"|"Linux")
                    pid_runtime=`ps -p ${pid} -oetime= | tr '-' ':' | awk -F: '{ total=0; m=1; } { for (i=0; i < NF; i++) {total += $(NF-i)*m; m *= i >= 2 ? 24 : 60 }} {print total}'`
                ;;
                "SunOS")
                    pid_runtime=`P_RUNTIME ${pid}`
                ;;
                esac

                # additional protection
                case ${pid_runtime} in
                "")
                 ;;
                *)
                 if [ ${pid_runtime} -gt ${endtime} ]; then
                     echo "`log_date`, ${HOST} WARN, old nmon process found due to: `ps auxwww | grep $pid | grep -v grep` killing (SIGTERM) process $pid"
                     kill $pid

                     # Allow some time for the process to end
                     sleep 5

                     # re-check the status
                     ps -p ${pid} -oetime= >/dev/null

                     if [ $? -eq 0 ]; then
                         echo "`log_date`, ${HOST} WARN, old nmon process found due to: `ps auxwww | grep $pid | grep -v grep` failed to stop, killing (-9) process $pid"
                         kill -9 $pid
                     fi

                 fi
                ;;
                esac
            fi

        done

    fi

    #
    # Maintenance task2
    # set -x
    # - manage any fifo reader orphan processes (no associated nmon process)
    # - manage any fifo reader duplicated (abnormal situation)

    echo "`log_date`, ${HOST} INFO, starting maintenance task 2: verify orphan or duplicated fifo_reader processes"

    for instance in fifo1 fifo2; do

    # Initiate
    oldPidNb=0

    case $INTERPRETER in
    "perl")
        readerNbProc=2 ;;
    "python"|"python3")
        readerNbProc=3 ;;
    esac

    # get the list of running processes
    ps auxwww | grep "nmon" | grep "splunk" | grep metricator_reader | grep ${instance} >/dev/null

    if [ $? -eq 0 ]; then

        oldPidList=`ps auxwwww | grep "nmon" | grep "splunk" | grep metricator_reader | grep ${instance} | grep -v grep | awk '{ print $2 }'`
        oldPidNb=`ps auxwww | grep "nmon" | grep "splunk" | grep metricator_reader | grep ${instance} | grep -v grep | wc -l | awk '{print $1}'`

        # search for associated nmon process
        case $UNAME in
        "AIX"|"Linux")
            ps auxwww | grep "nmon" | grep "splunk" | grep "var/log/metricator" | grep -v metricator_reader | grep ${instance} >/dev/null
        ;;
        "SunOS")
            ps auxwww | grep "sadc" | grep "splunk" | grep "var/log/metricator" | grep -v metricator_reader | grep ${instance} >/dev/null
        ;;
        esac

        if [ $? -ne 0 ] && [ $oldPidNb -eq $readerNbProc ]; then

            # no process found, kill the reader processes
            for pid in $oldPidList; do
                    echo "`log_date`, ${HOST} WARN, orphan reader process found (no associated nmon process) due to: `ps auxwww | grep $pid | grep -v grep` killing (SIGTERM) process $pid"
                    kill $pid

                    # Allow some time for the process to end
                    sleep 5

                    # re-check the status
                    ps -p ${pid} -oetime= >/dev/null

                    if [ $? -eq 0 ]; then
                    echo "`log_date`, ${HOST} WARN, orphan reader process (no associated nmon process) due to: `ps auxwww | grep $pid | grep -v grep` failed to stop, killing (-9) process $pid"
                        kill -9 $pid
                    fi
            done

        # If nmon is running but the number of reader processes is higher than 2 (shell parent + Python/Perl child), something went wrong
        elif [ $oldPidNb -gt $readerNbProc ]; then

            echo "`log_date`, ${HOST} WARN, multiple reader for the same fifo were detected, this is an abnormal situation and reader will be killed."

            # no process found, kill the reader processes
            for pid in $oldPidList; do
                    echo "`log_date`, ${HOST} WARN, duplicated reader process found due to: `ps auxwww | grep $pid | grep -v grep` killing (SIGTERM) process $pid"
                    kill $pid

                    # Allow some time for the process to end
                    sleep 5

                    # re-check the status
                    ps -p ${pid} -oetime= >/dev/null

                    if [ $? -eq 0 ]; then
                    echo "`log_date`, ${HOST} WARN, duplicated reader process found due to: `ps auxwww | grep $pid | grep -v grep` failed to stop, killing (-9) process $pid"
                        kill -9 $pid
                    fi
            done

        fi

    fi

    done

;;

# End of per OS case
esac

###### End maintenance tasks ######

###### Start cleaner ######

case ${INTERPRETER} in

"python"|"python3")
		$INTERPRETER $APP/bin/metricator_cleaner.py ${userargs} ;;

"perl")
		$APP/bin/metricator_cleaner.pl ${userargs} ;;

esac

exit 0
