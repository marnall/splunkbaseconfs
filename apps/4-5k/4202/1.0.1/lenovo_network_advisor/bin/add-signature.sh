#!/bin/sh

./signature.sh > /opt/splunk/etc/deployment-apps/lenovo_network_advisor/default/signature

mv /opt/splunk/etc/deployment-apps/lenovo_network_advisor/default/signature  /opt/splunk/etc/deployment-apps/lenovo_network_advisor/default/$(md5sum /opt/splunk/etc/deployment-apps/lenovo_network_advisor/default/signature | awk '{ print $1}') 
