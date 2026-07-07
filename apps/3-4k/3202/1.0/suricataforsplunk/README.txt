Suricata
----------------------------------------
        Author: Sergey Malinkin
        Feedback: malinkinsa@gmail.com
	Version: 1.0

Introduction
----------------------------------------
	Welcome to the Suricata app for Splunk.
This app contains field extraction for Suricata fast.log and separate field 
extraction for Suricata ssh.json log. Suricata ssh.json it's a separate log
for only ssh events (all ssh events in your traffic).

Aslo in app you can find two dashboard. 

 - First dashboard for analysis suricata fast.log Called Search for events. Suricata

 - Second dashboad for visual analisis ssh.json log with function for flexible analysis
by next field: data source, source and destination ip, server or client software, time. 
Caleed SSH Client's stats.

Additional applications.
----------------------------------------
Next applications required:

1. Python for Scientific Computing Add-on
	link:
		Mac: https://splunkbase.splunk.com/app/2881/
		Linux 64-bit: https://splunkbase.splunk.com/app/2882/
		Linux 32-bit: https://splunkbase.splunk.com/app/2884/
		Windows 64-bit: https://splunkbase.splunk.com/app/2883/

2. Machine Learning Toolkit and Showcase 
link: https://splunkbase.splunk.com/app/2890/

This app and add-on required for work some graphs with data

Example from my suricata.yaml
----------------------------------------
Section - outputs:

1. For fast.log

# a line based alerts log similar to Snort's fast.log
  - fast:
      enabled: yes
      filename: fast.log
      append: yes
      #filetype: regular # 'regular', 'unix_stream' or 'unix_dgram'

2. For ssh.json

 - eve-log:
      enabled: yes
      filetype: regular
      filename: ssh.json
      types:
        - ssh

Sourcetypes
----------------------------------------
You can find used sourcetype in next file - /opt/splunk/etc/apps/Suricata/default/props.conf
Use cp /opt/splunk/etc/apps/Suricata/default/props.conf /opt/splunk/etc/apps/Suricata/local/props.conf
for use this sourcetype.
