#!/bin/sh
while(true)
do
echo "[*] Changing directory to /opt/splunk/etc/deployment-apps/TA_Loki/bin "
cd /opt/splunk/etc/deployment-apps/TA_Loki/bin
ret_code=$?
if [ $ret_code != 0 ]; 
then 
echo "error in changing directory"
break;
fi
echo "[*] Successfully changed direcoty /opt/splunk/etc/deployment-apps/TA_Loki/bin"


echo "[*] running loki-upgrader.py"
python3 loki-upgrader.py --sigsonly
ret_code=$?
if [ $ret_code != 0 ]; 
then 
echo "error in running loki-upgrader.py"
break;
fi
echo "[*] Successfully upgraded loki signatures...signature-base folder will be under /opt/splunk/etc/deployment-apps/TA_Loki/bin/signature-base"


break
done
