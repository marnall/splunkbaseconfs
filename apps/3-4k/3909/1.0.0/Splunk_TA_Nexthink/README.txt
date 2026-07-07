# Nexthink® Add-on for Splunk® 

* This add-on includes Nexthink's data models associated with information sent 
* by the Nexthink Connector. In addition, the add-on provides eventtypes needed to leverage 
* usage of the CIM.

## OVERVIEW

- About the Nexthink Add-on for Splunk
- Release notes
- Support and resources

## INSTALLATION AND CONFIGURATION

- Hardware and software requirements
- Download
- Installation steps
- Configure Nexthink Add-on for Splunk

## USER GUIDE

- Data Models
- Eventtypes
- CIM Tags

---



### OVERVIEW


#### About the Nexthink Add-on for Splunk

| Author | Nexthink |
| Add-on Version | 1.0.0 |
| Vendor Products | Nexthink Connector |

The Nexthink Add-on for Splunk allows a Splunk Enterprise administrator to 
use new data models matching the data provided by the Nexthink Connector.


#### Release notes

##### About this release

Version 1.0.0 of the Nexthink Add-on for Splunk is compatible with:

| Splunk Enterprise versions | 6.5+ |
| CIM | 4.8 |
| Platforms | Platform independent |
| Vendor Products | Nexthink Connector |

##### New features

Nexthink Add-on for Splunk includes the following new features:

- 13 new data models matching the different types of events provided by Nexthink.
- 3 new eventtypes for those events in Nexthink having some correspondence with CIM models.


#### Support and resources

**Support**

For any help on this add-on, please contact support-splunk@nexthink.com



### INSTALLATION AND CONFIGURATION


#### Hardware and software requirements

##### Hardware requirements

Nexthink Add-on for Splunk supports the server platforms supported by Splunk Enterprise.

##### Software requirements

To function properly, Nexthink Add-on for Splunk doesn't require additional software:

##### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the Splunk Enterprise system requirements
(http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.


#### Download

Download the Nexthink Add-on for Splunk at https://splunkbase.splunk.com.


#### Installation steps

There are 3 options to install this add-on:

1. Via UI using "Manage Apps".
2. Via the command line using the following command:
   <$SPLUNK_HOME>/bin/splunk install app <$PATH_TO_SPL>/Splunk_TA_Nexthink.spl.
3. Directly extract the SPL file into <$SPLUNK_HOME>/etc/apps/ folder.



### USER GUIDE


#### Data Models

This add-on provides the data models knowledge for the following types of data from Nexthink:

** Connection events **
Represents a TCP connection or a UDP packet. 
Two child datasets: Failed Connections and Established Connections.

** Device Activity events **

Represents a device activity (boot or activity).
Currently only the Device Boot child dataset.

** Device Error events **

Represents a critical system error (system crash, hard reset or disk error).
Three child datasets: System Crash, SMART Disk Failure and Hard Reset.

** Device Warning events **

Represents a peak in device resource usage (CPU, memory or I/O).
Four child datasets: High IO Usage, High Memory Usage, High CPU Usage and High Number of Page Faults.

** Execution events **

Represents a process executing on a device.
No child datasets.

** Execution Error events **

Represents application errors (crash or not responding).
Two child datasets: Execution Crash and Execution Freeze.

** Execution Warning events **

Represents a peak in application resource usage (CPU or memory).
Two child datasets: High Application CPU and High Application Memory.

** Installation events **

Represents the installation or uninstallation of a Software packages (programs or updates).
Two child datasets: Package Installation and Package Uninstallation.

** Network Scan events **

Represents a sequence of failed TCP connections or UDP packets made to the same port to 
more than 50 destinations within a few seconds.
No child datasets.

** Port Scan events **

Represents a sequence of failed TCP connections or UDP packets made to the same destination
to more than 50 ports within a few seconds.
No child datasets.

** Printout events **

Represents a print job processed by a printer.
No child datasets.

** User Activity events **

Represents a user activity (logon or interactive activity).
Currently only the User Logon child dataset.

** Web Request events **

Represents HTTP or TLS requests.
Two child datasets: Established Web Requests and Failed Web Requests.


#### Eventtypes

The add-on contains 3 new eventtypes, supporting the following Common Information Model data models:

- Network Traffic
- Performance
- Web

** nxt_connection **

Tags Nexthink events belonging to the Connection category with the "communicate" and "network" tags,
thus matching the Network Traffic CIM's datamodel.

** nxt_execution **

Tags Nexthink events belonging to the Execution category with the "cpu" and "performance" tags,
thus matching the Performance CIM's datamodel.

** nxt_web_request **

Tags Nexthink events belonging to the Web Request category with the "web" tag, 
thus matching the Web CIM's datamodel.


#### CIM Tags:

- Network Traffic (All_Traffic dataset)
- Performance (All_Performance and CPU datasets)
- Web (Web dataset)
