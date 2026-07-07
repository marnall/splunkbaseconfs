#!/bin/sh

# Mandatory for AIX, prevents lib issues
case `uname` in
"AIX")
    unset LIBPATH ;;
esac

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

${APP}/bin/nmon_helper.sh 2>&1 | ${APP}/bin/hec_wrapper.sh $SPLUNK_HOME/var/log/nmon/nmon_collect.log nmon_collect collect:http

exit 0
