# Lenovo Network Advisor for Splunk

## Table of Contents

### OVERVIEW

- About the Lenovo Network Advisor app
- Release notes

### INSTALLATION
- Hardware and software requirements
- Installation steps 
- Deploy to single server instance
- Deploy by docker container 


### USER GUIDE

- Key concepts
- Data types
- Configure the Lenovo Network Advisor app
- Example Use Case-based Scenario

---
### OVERVIEW

#### About the  Lenovo Network Advisor App

| Author | Lenovo |
| --- | --- |
| App Version | 1.0.0 |
| Vendor Products | Lenovo CNOS Switches Version 10.8 and above   |
| Has index-time operations | False |
| Create an index | False |
| Implements summarization |  |

The Lenovo Network Advisor for Splunk app allows a Splunk® Enterprise administrator to analyze and visualize data from Lenovo CNOS switches  helping diagnose and troubleshoot Lenovo Switches, trends and providing insight into Networks having Lenovo Switches.

##### Scripts and binaries

The following Python scripts are included in the app. These are deployed to the forwarder and run in the forwarder only.

connect.py  - CNOS RESTAPI client Library
bstinfo.py - CNOS RESTAPI Buffer Utilization Library
sysInfo.py - CNOS RESTAPI systeminfo library
traffic_utlization.py - CNOS traffic utilization library
buffutil_check.py - script to get  buffer utlizaton from CNOS  Switch.
health_check.py  - script to get health statistics from CNOS Switch
traffic_check.py - script to get traffic utilization from CNOS Switch
congestion_check.py - script to get congestion statistics from CNOS switch

#### Release notes

##### About this release

Version 1.0.0 of the Lenovo Networks app is compatible with:

| Splunk Enterprise versions | 7.* |
| --- | --- |
| Platforms | Platform independent |
| Vendor Products | Lenovo CNOS version 10.8 and above|


## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

Lenovo supports the following server platforms in the versions supported by Splunk Enterprise:

- 2.6+ kernel Linux distributions (64-bit)
- 2.6+ kernel Linux distributions (32-bit)

#### Software requirements

To function properly, Lenovo Network Advisor requires the followingi software running on Lenovo Switches:

- CNOS version 10.8
- Install python 2.7 or higher and dependent ConcurrentLogHandler python library on Universal Forwarder

The customer has splunk enterprise server and one or more splunk forwarder software installed on their servers.  The customer downloads Lenovo Network Advisor splunk from Lenovo website or splunkbase and installs the app on splunk enterprise server. Each Splunk forwarder manages get switch data from Lenovo CNOS switch periodically and forwardes the data to the configured Splunk Server.

#### Download

 This app will be hosted in  splunkbase and also from lenovo website soon.

#### Installation steps
To install and configure this app on your supported platform, follow these steps:

1. In your Splunk Enterprise web interface, click on App(s) -> Manage Apps
1. Click on Install app from file
1. Select the file you downloaded, Click Upload, optionally selecting Upgrade app if you are upgrading from an earlier version. Restart Splunk.

##### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1. In your Splunk Enterprise web interface, click on App(s) -> Manage Apps
1. Click on Install app from file
1. Select the file you downloaded, Click Upload, optionally selecting Upgrade app if you are upgrading from an earlier version. Restart Splunk if required

2. On the server setting -> forwarder management
You should observe an forwarder connect to the server on clients tab. 
Create new server class to bind Lenovo Network Advisor to desired forwarders
3. Click on server setting -> forward management
    Click Apps tab, Create Apps for Lenovo Cloud Network Inspector
    select ‘restarted Splunkd’ 
4. Click on server setting -> forward management
Cick ‘Server Classes’tab  to bind Lenovo APP with forwarder clients with ‘Edit’ Action


##### Deploy in Docker Container
In this deployment the splunk server and splunk forwarder run as docker container in the same server.
Splunk in Docker container deployment example from bare Ubuntu 16.04 :
1.	sudo apt-get install docker-compose
2.	git clone https://github.com/chenyanyu/Lenovo_network_splunk_env.git
3.	cd  Lenovo_network_splunk_env/docker-compose
4.	sudo docker login
5.	sudo docker-compose -f lenovo-network-telemetry-splunk-all-in-one-1+1.yml  up
6.      Install the Lenovo Network Advisor App on the Splunk Enterprise Server container

#### Data types

This app provides search-time knowledge for the following types of data from Lenovo CNOS switches:

- Health -  Health data from the device. Comprises of Temperature,Fan, Power,CPU and Memory datesets
- Traffic - Traffic statistics from the devices
- Congestion - Congestion statistics  from the device 
- Buffer Utilization - Buffer Utilization counters from the device

The following saved searches are run every 5 minutes.  

1. CNOS_SYSTEMALERT - Scans for health related alerts 
2. CNOS_TRAFFICALERT - Scans for Traffic alerts alerts
3. CNOS_BSTALERT_DEVICE - Scans for Buffer Utilizaion Device Alerts on device
4. CNOS_BSTALERT_IPPG - Scans for Ingress Port Priority Group for Alerts
5. CNOS_BSTALERT_IPSP - Scans for Ingress Port Service Pool  for Alerts
6. CNOS_BSTALERT_EPSP - Scans for Egress Port Service Pool for Alerts
7. CNOS_BSTALERT_ISP  - Scans for Ingress Service Pool for Alerts
8. CNOS_BSTALERT_ESP - Scans for Egress Service Pool for Alerts
9. CNOS_BSTALERT_QUEUES - Scans for Egress CPU and RQE queues for Alerts  

####  Configuring the Lenovo Network Advisor App 

The Splunk Admin should know about  Splunk stores and searches data in different indexes and how roles apply to what indexes are searched.  The Setup menu page of the Lenovo Network Advisor for Splunk is used to configure Network Switches and map each switch to a Splunk Forwarder. Customer adds CNOS switches in the network through Lenovo Network Advisor Setup Graphical user interface. The app uses splunk deployment server to deploy python conversion scripts and some splunk configuration specific to the Lenovo Network Advisor for Splunk App.

### Example Use Case ###
* Find Congested ports
* View Network Utilization
* View critical Network Outages
* View Device Health Status
* Identify Switches experiencing Hardware Failure


