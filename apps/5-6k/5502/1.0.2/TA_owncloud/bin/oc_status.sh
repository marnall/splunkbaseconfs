#!/bin/sh                                                                                                
# Copyright (C) 2020 NetDescribe GmbH All Rights Reserved.  
cd $(dirname "$0")
#. ./metrics_api_key.sh
. ../local/owncloud.conf

if [ -z "$API_HOST" ]; then
  echo "ownCloud-API_HOST in local/owncloud.conf is not set!"
  exit 1
fi
RESULT=$(curl -s -k https://$API_HOST/status.php)
if [ $RESULT ]; then
	echo $RESULT
else
	echo "{\"fail\":\"Couldnt reach $HOST\"}"
fi