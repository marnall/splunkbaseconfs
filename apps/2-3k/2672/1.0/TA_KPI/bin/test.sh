#/opt/splunk/bin/splunk reload deploy-server -auth admin:La17xLD5vwpu
#/opt/splunk/bin/splunk cmd splunkd print-modinput-config meshblu meshblu://skynet_mydevices | /opt/splunk/bin/splunk cmd python /opt/splunk/etc/apps/Meshblu/bin/meshblu.py 

splunk cmd python ./blu.py __EXECUTE__ op=status
