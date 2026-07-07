# README.txt

### Description
This app watches critical registry settings needed for storing credentials in memory. Ideally this should always be disabled. 

You can read more here https://www.praetorian.com/blog/mitigating-mimikatz-wdigest-cleartext-credential-theft

### Installation/Platform
Splunk 8.0.1 tested
Windows 2016 tested

Create an index
Set index on inputs.conf and macros.conf
Install on Universal Forwarders, restart
Install on Heavy Forwarders, restart.
Install on Indexers, restart.
Install on Search heads, restart. 

### Usage
This app enabled tags for mimikats and attack for enabling this registry setting. 

### History
4.18.2020.1 - daniel, initial version

### Credits
Daniel Wilson <daniel.p.wilson@live.com>

### License
None

### TO DO/BUGS
1) Should I sed this data into something streamlined and into it's own sourcetype? 
