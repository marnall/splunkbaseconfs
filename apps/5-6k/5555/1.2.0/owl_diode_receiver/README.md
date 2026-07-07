
# Introduction

This application is intended to run on a Splunk Indexer
and receive raw data with Splunk meta data from the
Splunk Owl Diode Sender app.

To configure this, enable a listening port with the `diode-syslog`
sourcetype as documented here: 
https://docs.splunk.com/Documentation/Splunk/latest/Data/Monitornetworkports

Create a `local/inputs.conf` and listen to either TCP or UDP. The
traffic type and listening port need to match the Owl sender Add-On.
The sourcetype is `diode-syslog`. TCP can be configured from the
GUI, the UDP input needs additional options and needs be configured
via `inputs.conf`

For TCP:
```
# Listen on a TCP port to receive syslog traffic from the diode
# Configure incoming TCP syslog to not append a timestamp or hostname.
# TCP does not strip the priority byte by default.
[tcp://6003]
disabled = 0
sourcetype = diode-syslog
```

For UDP:
```
# Listen on a UDP port to receive syslog traffic from the diode
# Configure incoming UDP syslog to not append a timestamp or hostname.
# UDP strips the priority byte by default. Keep it to be consistent with TCP.
[udp://6004]
disabled = 0
no_appending_timestamp = true
no_priority_stripping = true
sourcetype = diode-syslog
```

---- Release Notes ----

v1.0: May 2021
        - Initial release
		
v1.1: March 2024
		- Configuration for large events
