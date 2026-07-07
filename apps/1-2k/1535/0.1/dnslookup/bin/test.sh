#!/bin/bash -x

cat sample.csv | /opt/splunk/bin/splunk cmd python dnslookup.py reverse ip fqdn
#cat sample.csv | /opt/splunk/bin/splunk cmd python serviceslookup.py port service_name
