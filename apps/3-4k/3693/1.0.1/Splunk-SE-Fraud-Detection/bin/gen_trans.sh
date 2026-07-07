#!/bin/sh

###OUTPUT_FILE="/tmp/bank_manual_enter.log"
############################
SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")
FNAME="/../../TMP/bank_manual_enter.log"
OUTPUT_FILE=$SCRIPTPATH$FNAME
############################

DATE="`date +%Y-%m-%d`"
TIME="`date +%H:%M:%S`"

# 2015-12-30 14:19:49 TR_IP_ADDRESS=Young TR_SVC=INTERNET TR_STATUS=success TR_ITEM_ID=EST-19 TR_SESSION_ID=SD10SL3FF9ADFF4 TR_AMOUNT=1000 TR_CHANNEL=http://www.globalbank.com TR_ACTION=fund_transfer TR_ITEM_ID=EST-19 TR_TARGET_ACCT=001 TR_ACCESS_TYPE=Mozilla_5_0 TR_DEV_TYPE=Windows TR_BROWSER_TYPE=Windows NT 5.1; en-GB; rv:1.8.1.6 TR_SESSION_TIME=803

echo "
============================================================
SPLUNK FUND TRANSFER TRANSATION GENERATOR
============================================================
"
echo -n "Enter your account ID  [ like : mjackson ] : "
read USER

echo -n "Enter target bank [ like : bank_of_splunk ] : "
read TARGET_BANK

echo -n "Enter target acount [ like : friend_01 ] : "
read TARGET_ACCT

echo -n "Enter wire amount [ like : 500 ] : "
read AMOUNT

LOG="$DATE $TIME TR_IP_ADDRESS=$USER TR_SVC=INTERNET TR_STATUS=success TR_ITEM_ID=EST-19 TR_SESSION_ID=SD10SL3FF9ADFF4 TR_AMOUNT=$AMOUNT TR_CHANNEL=http://www.globalbank.com TR_ACTION=fund_transfer TR_ITEM_ID=EST-19 TR_TARGET_ACCT=${TARGET_ACCT} TR_ACCESS_TYPE=Mozilla_5_0 TR_DEV_TYPE=Windows TR_BROWSER_TYPE=Windows NT 5.1; en-GB; rv:1.8.1.6 TR_SESSION_TIME=803"

echo $LOG >> $OUTPUT_FILE

echo "
============================================================
INSERTED EVENT : $DATE $TIME
============================================================
$LOG
============================================================

"
