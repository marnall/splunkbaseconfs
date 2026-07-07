# README.txt

This app is written with Splunk ES in mind with intentions of solving PCI related asks. It might work with Splunk for PCI with some adjustments. Works with Splunk Core as well but you're missing some cool benefits without Splunk ES. 

Works on centOS 5, 6 and 7 as well as Ubuntu 14.04. The props.conf/transforms.conf work great for Windows as well but the inputs.conf would need to be adjusted. 

# Install 
1) Install auditbeat and configure it to log locally (see below)
2) Install Splunk Universal Forwarder, restart
3) Push this app to the Universal Forwarder, restart
4) Push this app to the indexes and heavy forwarders, restart
5) Push this app to any search heads, restart
6) Craft aletrs and dashboards
7) Happy Splunking! 

Splunk Add-on Auditbeat version 1.0.0

Auditbeat documentation, see: https://www.elastic.co/guide/en/beats/auditbeat/current/index.html
FIM reading, see: https://isc.sans.edu/forums/diary/What+to+watch+with+your+FIM/20897/

# PCI 
Deploy file integrity monitoring software to alert personnel to unauthorized modification of critical system files, configuration files or content files. Configure the software to perform critical file comparisons at least weekly.

# Auditbeat.yml
Do what ever you gotta do to onboard the data. But an easy approach is simply to instruct auditbeat to log locally and pick up the data with a Splunk Universal Forwarder. 

auditbeat.modules:
- module: file_integrity
  paths:
  - /bin
  - /usr/bin
  - /sbin
   -/usr/sbin
   -/etc

### File outputs
  output.file:
    enabled: true
    path: "/var/log/auditbeat/logs"
    filename: auditbeat
    rotate_every_kb: 10000
    number_of_files: 3
    permissions: 0600

# FSCHANGE
Our auditor wanted to ensure something was watching the watcher. So as a quick and free solution I enabled fschange on the auditbeat config file and this satisfied the audit requirement. This has practical application as well with rogue admins.  

The included fschange in inputs.conf is an old but function feature in Splunk that they'd rather we retire. If this config conflicts with any of your existing FSCHANGE stanzas in other apps you will get errors such as change alerts that invalid. Additionally fschange simply may not work on your version of Splunk as the feature deprecated in releases (working as of 7.2.5 and earlier for me). If you don't like it - disable it. 

If you prefer not to use FSCHANGE but want to ensure you have cross monitoring in place consider AIDE which comes with most Linux distributions.

https://docs.splunk.com/Splexicon:Filesystemchangemonitor

# Splunk_TA_nix
It would be common to deploy Splunk_TA_nix with this package to monitor that the auditbeat service is running. If there is demand I'll move a service check script into this app. But really you should just use Splunk_TA_nix for that. 

# sourcetype
I personally wante to seperate the auditd and fim events into their own sourcetypes for log retention, ease of data management and general performance concerns. All auditbeat data is sourcetype=auditbeat but FIM events are moved to auditbeat-fim by the transforms.conf file. 

... Shout out to Nick and Mike for the push