#!/bin/sh

# set -x

# Program name: nmon2kv.sh
# Compatibility: sh
# Purpose - Shell wrapper for nmon2kv.py / nmon2kv.pl
# Author - Guilhem Marchand
# Disclaimer: This script is provided as it is, with absolutely no warranty
# Date of first publication - Jan 2016

# Licence:

# Copyright 2016 Guilhem Marchand

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Releases Notes:

# - Jan 2014, V1.0.0: Guilhem Marchand, Initial version
# - 2017/07/24, V1.0.1: Guilhem Marchand, interpreter choice update

# Version 1.0.1

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

if [ -z "${SPLUNK_HOME}" ]; then
	echo "`log_date`, ERROR, SPLUNK_HOME variable is not defined"
	exit 1
fi

# Set tmp directory
APP_VAR=${SPLUNK_HOME}/var/log/nmon

# Verify it exists
if [ ! -d ${APP_VAR} ]; then
    mkdir -p ${APP_VAR}
	exit 1
fi

# silently remove tmp file (testing exists before rm seems to cause trouble on some old OS)
rm -f ${APP_VAR}/nmon2csv.temp.*

# Set nmon_temp
nmon_temp=${APP_VAR}/nmon2csv.temp.$$

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

#
# Interpreter choice
#

PYTHON=0
PERL=0
# Set the default interpreter
INTERPRETER="python"

# Get the version for both worlds
PYTHON=`which python >/dev/null 2>&1`
PERL=`which python >/dev/null 2>&1`

case $PYTHON in
*)
   python_subversion=`python --version 2>&1`
   case $python_subversion in
   *" 2.7"*)
    PYTHON_available="true" ;;
   *)
    PYTHON_available="false"
   esac
   ;;
0)
   PYTHON_available="false"
   ;;
esac

case $PERL in
*)
   PERL_available="true"
   ;;
0)
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
           INTERPRETER="python" ;;
 esac
;;

# Other OS, priority is Python
*)
     case $PYTHON_available in
     "true")
           INTERPRETER="python" ;;
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

"python")
    cat ${nmon_temp} | ${SPLUNK_HOME}/bin/splunk cmd ${APP}/bin/nmon2kv.py --nmon_var ${SPLUNK_HOME}/var/log/nmon --nmon_app ${APP} ${userargs} ;;

"perl")
	cat ${nmon_temp} | ${SPLUNK_HOME}/bin/splunk cmd ${APP}/bin/nmon2kv.pl --nmon_var ${SPLUNK_HOME}/var/log/nmon --nmon_app ${APP} ${userargs} ;;

esac

# Remove temp
rm -f ${nmon_temp}

exit 0
