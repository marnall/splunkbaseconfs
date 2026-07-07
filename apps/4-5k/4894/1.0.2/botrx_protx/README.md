# Overview
The BotRx Protx for Splunk is to help BotRx ProTx customers to integrate their ProTx appliance into Splunk system. It provides two sourcetypes for customer to choose based on their deployment needs, as well as dashboard to show threat events detected by ProTx appliance.

# Supported Splunk Versions
7.0.0 and above

# Platform requirement
Platform Independent

# Source types
This app contains predefined source types that Splunk Enterprise uses to ingest incoming events and categorize these events for search.
The source types are based on the data sources that the app ingests. 
Many of the source types support data models in the Common Information Model.
Source type | Collection method  |
--- | --- |
botrx:protx:syslog | UDP/TCP/file over syslog protocol
botrx:protx:json | HTTP/HTTPS/file without syslog header

# Installation  
This app should be installed on the indexers and search heads.

# Configuration
1. Configure your BotRx ProTx servers to send data to the syslog server or the Splunk indexer.
2. Follow the steps based on where the ProTx servers send data to the Splunk system: 
- If the ProTx servers send data to the Splunk indexer directly,please configure the TCP/UDP inputs and set botrx:protx:syslog as the source type.
- If the ProTx servers send data to syslog server and Unviersal Forwarder into the Splunk system, please follow below steps:
a.Configure the syslog server to filter by PROGRAMNAME, store the MSG into the file.
b. Configure the UF to monitor the file, set botrx:protx:json as the source type.
- If the ProTx servers send data to syslog server and HEC into the Splunk system, please follow below steps:
a. Create HEC token on the Splunk.
b. Configure the syslog server to filter by PROGRAMNAME, set botrx:protx:json as the source type, MSG as the event body, then send to the Splunk system.

# Resources and Support
Questions and feature requests (BotRx ProTx app specific): sarah@botrx.com, or supportservice1@botrx.com

# Release Notes
- Version 1.0.2:
1. Support ProTx 3.0+



