# README.txt

Add-on for Arista version 1.0.0 - 
Forked and Derived from Official Arista app, see: https://splunkbase.splunk.com/app/1918

I found the official App for Arista was missing some field extractions, eventtypes and tags that are needed for Splunk ES and Splunk for PCI so I added them. Removed the other stuff. Official app needed an embedded forwarder this does not. 

Configure Your Switch - 
Since this app does not use an embedded forwarder on the eOS platform you need to ensure syslog properly configured. Here is my recommended config for a Splunk ES environment. 

### config t ###
 logging console warnings
 logging host 1.2.3.4
 logging source-interface Vlan66
 logging level aaa info
 logging level accounting info
 logging level security info
 logging format timestamp high-res
 logging format hostname fqdn

Install - 
0) Configure your switch
1) Collect your Arista data via Syslog and sourcetype it as arista_switch_log
2) Install this app on your indexers (and head forwarders if you them), restart
3) Install this app on your search heads, restart
4) Done! 

Timestamps - 
Please note timestamps are not configured in my props.conf out of box. I recommend you configure your switch to "logging format timestamp high-res" to ensure the year and sub-second precison on your logs. What ever you select ensure you note your timestamp in props.conf. 
Standard - Apr  8 08:14:21

FAQ - 
Q. What's different from the official app?
A. This TA Is for you to build your Splunk SIEM solutions on while the official app is a operations monitornig solution. But there is overlap as my base is just a fork of their app. 
- I removed the telemetry components of the official app 
- I remove the GUI
- The Embedded forwarder is not required, I assume syslog in my case
- Sdded the needed enhancement for interaction with Splunk SIEM solutions (eventtypes and tags)

Q. Which App should I use, this one or the official one? 
A. If you are using Splunk ES's data models you want this one, otherwise use the official app. 

Q. What if I want the operational benefit of the official app are your tags? 
A. Install the official app and take eventtypes.conf, props.conf and tags.conf from this app and add them as "local" on your search head. You're gonna need to do a lot of tuning. 