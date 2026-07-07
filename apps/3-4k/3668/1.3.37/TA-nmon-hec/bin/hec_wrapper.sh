#!/bin/sh

# set -x

# Program name: hec_wrapper.sh
# Purpose - stream to Splunk HEC
# Author - Guilhem Marchand
# Disclaimer:  this provided "as is".
# Date - June 2014

# Version 1.0.1
# 2017/08/21, Guilhem Marchand: SunOS compatibility issue with GNU grep

# For AIX / Linux / Solaris

#################################################
## 	Your Customizations Go Here            ##
#################################################

# format date output to strftime dd/mm/YYYY HH:MM:SS
log_date () {
    date "+%d-%m-%Y %H:%M:%S"
}

# Which type of OS are we running
UNAME=`uname`

# file destination
log_file=$1

# Splunk sourcetype
splunk_sourcetype=$2

# Splunk source
splunk_source=$3

# APP path discovery
if [ -d "$SPLUNK_HOME/etc/apps/TA-nmon" ]; then
        APP=$SPLUNK_HOME/etc/apps/TA-nmon

elif [ -d "$SPLUNK_HOME/etc/slave-apps/TA-nmon" ];then
        APP=$SPLUNK_HOME/etc/slave-apps/TA-nmon

elif [ -d "$SPLUNK_HOME/etc/apps/TA-nmon-hec" ]; then
        APP=$SPLUNK_HOME/etc/apps/TA-nmon-hec

elif [ -d "$SPLUNK_HOME/etc/slave-apps/TA-nmon-hec" ];then
        APP=$SPLUNK_HOME/etc/slave-apps/TA-nmon-hec

else
        echo "`log_date`, ${HOST} ERROR, the APP directory could not be defined, is the TA-nmon/TA-nmon-hec installed ?"
        exit 1
fi

# source default nmon.conf
if [ -f $APP/default/nmon.conf ]; then
	. $APP/default/nmon.conf
fi

# source local nmon.conf, if any

# Search for a local nmon.conf
if [ -f $APP/local/nmon.conf ]; then
	. $APP/local/nmon.conf
fi

# On a per server basis, you can also set in /etc/nmon.conf
if [ -f /etc/nmon.conf ]; then
	. /etc/nmon.conf
fi

# AIX and Solaris are not GNU grep friendly, but have always Perl available

case `uname` in

"AIX"|"SunOS")

    # Capture the splunk_http_url
    splunk_http_url=`echo $nmon2csv_options | perl -ne '/splunk_http_url\s([^\s]*+)/ && print $1."\n"'`

    # Capture the splunk_http_token
    splunk_http_token=`echo $nmon2csv_options | perl -ne '/splunk_http_token\s([^\s]*+)/ && print $1."\n"'`
;;

*)

    # Capture the splunk_http_url
    splunk_http_url=`echo $nmon2csv_options | grep -Po "splunk_http_url\s{0,}\K[^\s]*"`

    # Capture the splunk_http_token
    splunk_http_token=`echo $nmon2csv_options | grep -Po "splunk_http_token\s{0,}\K[^\s]*"`
;;

esac

# Manage FQDN option
echo $nmon2csv_options | grep '\-\-use_fqdn' >/dev/null
if [ $? -eq 0 ]; then
    HOST=`hostname -f`
else
    HOST=`hostname`
fi

# Manage optional write to local file system
echo $nmon2csv_options | grep '\-\-no_local_log' >/dev/null
if [ $? -eq 0 ]; then
    NO_LOCAL_LOG="True"
else
    NO_LOCAL_LOG="False"
fi

# Check curl availability
which curl >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "`log_date`, ${HOST} ERROR, the curl command could not be found, cannot stream to Splunk HEC without curl"
fi

############################################
# functions
############################################

# Store stdin
output=""
while read line ; do

    # Write to local file system if option has been set
    case $NO_LOCAL_LOG in
    "False")
        echo "$line" >> ${log_file} ;;
    esac

	case $output in
	"")
	    output="$line"
	    ;;
	*)
	    output="$output\n$line"
	    ;;
	esac
done

# Stream to HEC
case ${splunk_http_token} in

"insert_your_splunk_http_token")
	# Do nothing
;;

*)
	curl -s -k -H "Authorization: Splunk ${splunk_http_token}" ${splunk_http_url} -d "{\"host\": \"${HOST}\", \"sourcetype\": \"${splunk_sourcetype}\", \"source\": \"${splunk_source}\", \"event\": \"${output}\"}" 2>&1 >/dev/null
;;

esac

exit 0
