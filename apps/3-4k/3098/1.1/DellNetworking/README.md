# Dell Networking

## Table of Contents

### OVERVIEW
- About the Dell Networking app
- Release notes

### INSTALLATION
- System requirements
- Installation steps 

### USER GUIDE
- Key concepts
- Data types

---
### OVERVIEW

#### About the Dell Networking app

| Author | Dell Networking |
The Dell Networking App for Splunk Enterprise includes dashboards, data models and logic for analyzing data from Dell Switch devices using Splunk® Enterprise.

## INSTALLATION AND CONFIGURATION

### System requirements
Dell Networking supports the following server platforms in the versions supported by Splunk Enterprise:
- CentOS release 6.7 +

#### Installation steps
Step 1: App installation
1.Install the Dell Networking App on your search head 
2.Syslog input: Enable an UDP input with a custom port number on your Splunk indexer. Set the sourcetype to dell-networking
Step 2: Configure your Dell switches
1.Add the hostname or IP address of the Splunk server to the list of syslog destination targets. For instance:
Dell(conf)# logging 10.20.30.40 udp 1234
2.Configure the timestamps of the syslogs to include the switch local time
Dell(conf)# service timestamps log datetime show-timezone localtime
Notes:
Dell Networking App is compatible with Dell switches running OS9 and Splunk 6.3 or later
You can use the dellsyslog utility to generate custom events from the CLI or from scripts running on switches
These events will be displayed in the Custom Events dashboard.
For example, this command will generate a critical syslog:
$ dellsyslog -s critical "My monitor error"

## USER GUIDE

### Key concepts for Dell Networking
The Splunk Admin must know how to configure data inputs and how Splunk stores and searches data in different indexes and how roles apply to what indexes are searched. 

### Data types
This app provides search-time knowledge for the following types of data:
- dell-networking - Syslog events from your devices




