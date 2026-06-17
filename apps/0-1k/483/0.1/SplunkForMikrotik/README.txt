Introduction
------------
Welcome to the Splunk for Mikrotik App.
This app provides field extractions for mikrotik

Installation
------------
To install this app, extract the .spl file to $SPLUNK_HOME/etc/apps/

You will need to also setup your RouterOS with a Log & Log action as below


#Edit the IP address for remote and the port for remote-port to reflect your splunk/syslog install
/system logging action
add bsd-syslog=no name=splunk remote=1.2.3.4 remote-port=514 \
    src-address=0.0.0.0 syslog-facility=local6 syslog-severity=auto target=\
    remote
/system logging
add action=splunk prefix=""






Please also ensure to setup your splunk input to have the source type defined as mikrotik


