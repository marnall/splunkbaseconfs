#!/bin/bash

#export LC_CTYPE=zh_CN.utf8

PATH=./phantomjs/bin:$PATH
cd `dirname $0`

if [ -z $4 ]; then
  ts="report"`date +%Y%m%d`
else
  ts=$4`date +%Y%m%d`
fi

./casperjs/bin/casperjs screenshot.js "$2" 30 "$ts" >> cron.log

tmp_mail=`mktemp -t splunk_reportXXX`

echo Daily report for `date` > $tmp_mail
email=$2
echo $email >> $tmp_mail

#for pdf in *.png; do
#    uuencode $pdf `basename $pdf` >> $tmp_mail
#done

#for pdf in *.pdf; do
#    uuencode $pdf `basename $pdf` >> $tmp_mail
#done

#mailx -a report.png -a cups_alert.pdf -s "$3" -S smtp=smtp://145.4.34.11 -S from="demo@unionpay.com" "$1"  < $tmp_mail
mailx -a "$ts.png" -a "$ts.pdf" -s "$3" "$1"  < $tmp_mail
echo mail sent
