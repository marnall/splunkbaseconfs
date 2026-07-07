#!/bin/bash
# works
# the time function for auditreduce is honestly not great, and the greatest accuracy i can get is down to the hour
settime="$(date -v-120M "+%Y%m%d%H")"
now="$(date -v-60M "+%Y%m%d%H")"

# seek file logic taken from the auditd input rlog in splunks app
MYFILE=$SPLUNK_HOME/var/run/splunk/bsm_audit_seekfile

if [ -e $MYFILE ] ; then
	SEEK=`head -1 $MYFILE`
else
	SEEK=19910101
	echo "19910101" > $MYFILE
fi


auditreduce -a $SEEK -b $now /var/audit/* | praudit 2>/dev/null

echo $now > $MYFILE

exit 0
