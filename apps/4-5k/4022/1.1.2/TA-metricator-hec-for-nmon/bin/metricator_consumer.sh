#!/bin/sh

# set -x

# Program name: metricator_consumer.sh
# Purpose - consume data produced by the fifo readers
# Author - Guilhem Marchand

# Version 2.0.0

# For AIX / Linux / Solaris

#################################################
## 	Your Customizations Go Here            ##
#################################################

# hostname
HOST=`hostname`

# Which type of OS are we running
UNAME=`uname`

# format date output to strftime dd/mm/YYYY HH:MM:SS
log_date () {
    date "+%d-%m-%Y %H:%M:%S"
}

if [ -z "${SPLUNK_HOME}" ]; then
	echo "`log_date`, ${HOST} ERROR, SPLUNK_HOME variable is not defined"
	exit 1
fi

# check and wait to acquire mutex
mutex="$SPLUNK_HOME/var/log/metricator/mutex"

remove_mutex () {
    rm -f $mutex
}

# Allow 10s mini to acquire mutex and break
count=0
while [ -f $mutex ]; do
    sleep 2
    count=`expr $count + 1`
    if [ $count -gt 5 ]; then
        break
    fi
done

# acquire mutex
if [ -d $SPLUNK_HOME/var/log/metricator ]; then
  touch $mutex
fi

# tmp dir and file
temp_dir="${SPLUNK_HOME}/var/log/metricator/tmp/"

if [ ! -d ${temp_dir} ]; then
    mkdir -p ${temp_dir}
fi

temp_file="${temp_dir}/metricator_consumer.sh.$$"

# Splunk Home variable: This should automatically defined when this script is being launched by Splunk
# If you intend to run this script out of Splunk, please set your custom value here
SPL_HOME=${SPLUNK_HOME}

# Check SPL_HOME variable is defined, this should be the case when launched by Splunk scheduler
if [ -z "${SPL_HOME}" ]; then
	echo "`log_date`, ${HOST} ERROR, SPL_HOME (SPLUNK_HOME) variable is not defined"
	remove_mutex
	exit 1
fi

# APP path discovery
if [ -d "$SPLUNK_HOME/etc/apps/TA-metricator-hec-for-nmon" ]; then
        APP=$SPLUNK_HOME/etc/apps/TA-metricator-hec-for-nmon

elif [ -d "$SPLUNK_HOME/etc/peer-apps/TA-metricator-hec-for-nmon" ];then
        APP=$SPLUNK_HOME/etc/peer-apps/TA-metricator-hec-for-nmon

else
        echo "`log_date`, ${HOST} ERROR, the APP directory could not be defined, is the TA-metricator-hec-for-nmon installed ?"
        remove_mutex
        exit 1
fi

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

# default values relevant for our context
nmonparser_options="--mode fifo"

# source default nmon.conf
if [ -f $APP/default/nmon.conf ]; then
    # During initial deployment, the nmon.conf needs to be managed properly by the metricator_consumer.sh
    # wait for this to be done
    grep '\[nmon\]' $APP/default/nmon.conf >/dev/null
    if [ $? -eq 0 ]; then
        echo "`log_date`, ${HOST} INFO, initial deployment condition detected, safe exiting."
        exit 0
    else
        . $APP/default/nmon.conf
    fi
fi

# source local nmon.conf, if any

# Search for a local nmon.conf file located in $SPLUNK_HOME/etc/apps/TA-metricator-hec-for-nmon/local
if [ -f $APP/local/nmon.conf ]; then
        . $APP/local/nmon.conf
fi

# On a per server basis, you can also set in /etc/nmon.conf
if [ -f /etc/nmon.conf ]; then
	. /etc/nmon.conf
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

############################################
# functions
############################################

# consume function
consume_data () {

# fifo name (valid choices are: fifo1 | fifo2)
FIFO=$1

# consume fifo

# realtime
nmon_config=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_config.dat
nmon_header=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_header.dat
nmon_timestamp=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_timestamp.dat
nmon_data=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_data.dat
nmon_data_tmp=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_data_tmp.dat
nmon_external=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_external.dat
nmon_external_header=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_external_header.dat


# rotated
nmon_config_rotated=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_config.dat.rotated
nmon_header_rotated=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_header.dat.rotated
nmon_timestamp_rotated=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_timestamp.dat.rotated
nmon_data_rotated=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_data.dat.rotated
nmon_external_rotated=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_external.dat.rotated
nmon_external_header_rotated=$SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/nmon_external_header.dat.rotated

# manage rotated data if existing, prevent any data loss

# all files must be existing to be managed
if [ -s $nmon_config_rotated ] && [ -s $nmon_header_rotated ] && [ -s $nmon_data_rotated ]; then

    # Manager headers
    unset nmon_header_files
    if [ -f $nmon_external_header_rotated ]; then
        nmon_header_files="$nmon_header_rotated $nmon_external_header_rotated"
    else
        nmon_header_files="$nmon_header_rotated"
    fi

    # Ensure the first line of nmon_data starts by the relevant timestamp, if not add it
    head -1 $nmon_data_rotated | grep 'ZZZZ,T' >/dev/null
    if [ $? -ne 0 ]; then
        # check timestamp dat exists before processing
        # there is no else possible, if the the timestamp data file does not exist, there is nothing we can do
        # and the parser will raise an error
        if [ -f $nmon_timestamp_rotated ]; then
            tail -1 $nmon_timestamp_rotated >$temp_file
            cat $nmon_config_rotated $nmon_header_files $temp_file $nmon_data_rotated $nmon_external_rotated | $SPLUNK_HOME/bin/splunk cmd $APP/bin/nmonparser.sh $nmonparser_options
        fi
    else
        cat $nmon_config_rotated $nmon_header_files $nmon_data_rotated $nmon_external_rotated | $SPLUNK_HOME/bin/splunk cmd $APP/bin/nmonparser.sh $nmonparser_options
    fi

    # remove rotated
    rm -f $SPLUNK_HOME/var/log/metricator/var/nmon_repository/$FIFO/*.dat.rotated

    # header var
    unset nmon_header_files

fi

# Manage realtime files

# all files must be existing to be managed
if [ -s $nmon_config ] && [ -s $nmon_header ] && [ -s $nmon_data ]; then

    # get data mtime
    case $INTERPRETER in
    "perl")
        perl -e "\$mtime=(stat(\"$nmon_data\"))[9]; \$cur_time=time();  print \$cur_time - \$mtime;" >$temp_file
        nmon_data_mtime=`cat $temp_file`
        ;;
    "python"|"python3")
        $INTERPRETER -c "import os; import time; now = time.strftime(\"%s\"); print(int(int(now)-(os.path.getmtime('$nmon_data'))))" >$temp_file
        nmon_data_mtime=`cat $temp_file`
        ;;

    esac

    # file should have last mtime of mini 5 sec

    while [ $nmon_data_mtime -lt 5 ];
    do

        sleep 1

        # get data mtime
        case $INTERPRETER in
        "perl")
            perl -e "\$mtime=(stat(\"$nmon_data\"))[9]; \$cur_time=time();  print \$cur_time - \$mtime;" >$temp_file
            nmon_data_mtime=`cat $temp_file`
            ;;
        "python"|"python3")
            $INTERPRETER -c "import os; import time; now = time.strftime(\"%s\"); print(int(int(now)-(os.path.getmtime('$nmon_data'))))" >$temp_file
            nmon_data_mtime=`cat $temp_file`
            ;;
        esac


    done

    # copy content
    cat $nmon_data > $nmon_data_tmp

    # nmon external data
    if [ -f $nmon_external ]; then
        cat $nmon_external >> $nmon_data_tmp
    fi

    # empty the nmon_data file & external
    > $nmon_data
    > $nmon_external

    # Manager headers
    unset nmon_header_files
    if [ -f $nmon_external_header ]; then
        nmon_header_files="$nmon_header $nmon_external_header"
    else
        nmon_header_files="$nmon_header"
    fi

    # Ensure the first line of nmon_data starts by the relevant timestamp, if not add it
    head -1 $nmon_data_tmp | grep 'ZZZZ,T' >/dev/null
    if [ $? -ne 0 ]; then
        tail -1 $nmon_timestamp >$temp_file
        cat $nmon_config $nmon_header_files $temp_file $nmon_data_tmp | $SPLUNK_HOME/bin/splunk cmd $APP/bin/nmonparser.sh $nmonparser_options
    else
        cat $nmon_config $nmon_header_files $nmon_data_tmp | $SPLUNK_HOME/bin/splunk cmd $APP/bin/nmonparser.sh $nmonparser_options
    fi

    # remove the copy
    rm -f $nmon_data_tmp

    # header var
    unset nmon_header_files

fi

}

####################################################################
#############		Main Program 			############
####################################################################

# consume fifo1
consume_data fifo1

# allow 1 sec idle
sleep 1

# consume fifo2
consume_data fifo2

# remove the temp file
if [ -f $temp_file ]; then
    rm -f $temp_file
fi

remove_mutex
exit 0
