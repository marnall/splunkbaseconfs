This is a TA for the EdgeRouter X to make its logs CIM compliant.


This TA assumes the following:

You are using sourcetype=syslog
Rule names are in the following format:  srczone_TO_destzone
WAN interface =eth0
LAN interface = eth1*


You should only have to edit the EXTRACT-syslog and direction statements in props.conf


1.0.1
Fixed typo in props.conf
