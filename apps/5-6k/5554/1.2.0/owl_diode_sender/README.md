
# Introduction

This Add-On forwards data from a Splunk Heavy Forwarder over a syslog TCP/UDP
transport to an indexer. It is intended to be used with the Owl Diode
Receiver app.

This application sends data directly through the syslog output
processor.

The output for syslog over TCP and UDP sent on the wire will look like this:
```
<42>Oct 29 19:12:45 diode-sender t=1540825965|st=splunkd|s=/opt/diode/splunk-sender/var/log/splunk/metrics.log|h=diode-sender|r=10-29-2018 19:12:45.746 +0400 INFO  Metrics - .....`
```

# Sending with Splunk outputs.conf

## outputs.conf

Keep the syslog PRI code and hostname and timestamp to stick to the
syslog RFC. Some diodes check format.  The PRI code is 42 for obvious
reasons.

### TCP transport

Create a `local/outputs.conf`:
```
[syslog:diode-syslog-tcp]
disabled = false
server = 127.0.0.1:6003
```
This syslog-stanza MUST be called 'diode-syslog-tcp' and is referenced in transforms.conf

### UDP transport

Create a `local/outputs.conf`:
```
[syslog:diode-syslog-udp]
disabled = false
server = 127.0.0.1:6004
```
This syslog-statement MUST be called 'diode-syslog-udp' and is referenced in transforms.conf

## props.conf

In `props.conf` edit the sourcetypes you want to forward, or use `default` to send everything.

Sample `local/props.conf`:
```
[default]
TRANSFORMS-diode-1-rewrite=add_host, add_source, add_sourcetype, add_time, add_index
TRANSFORMS-diode-2-outputs=send-to-syslog-udp
```

---- Release Notes ----

v1.0: May 2021
        - Initial release
		
v1.1: March 2024
		- Configuration for large events