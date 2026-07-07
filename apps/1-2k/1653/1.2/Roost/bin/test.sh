/opt/splunk/bin/splunk cmd splunkd print-modinput-config roost roost://Test \
   | /opt/splunk/bin/splunk cmd python /opt/splunk/etc/apps/Roost/bin/roost.py
