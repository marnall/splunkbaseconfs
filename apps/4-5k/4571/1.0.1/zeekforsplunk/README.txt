Please ensure that you also using the Splunk Add-on for Zeek aka bro(https://splunkbase.splunk.com/app/1617/) with this app.

Adjust the custom macro `zeeklogs` to point to the index that contains you Zeek logs. 

Sample  inputs.conf for use on the Splunk UF installed on the zeek sensor:

[monitor:///usr/local/bro/logs/current/conn.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/dns.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/software.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/smtp.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/ssl.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/ssh.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/x509.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/ftp.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/http.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/rdp.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/smb_files.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/smb_mapping.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/snmp.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/sip.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/files.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/dhcp.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/weird.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/stats.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json

[monitor:///usr/local/bro/logs/current/capture_loss.log]
_TCP_ROUTING = *
index = zeek
sourcetype = bro:json
