****Block Solutions CMX Monitoring TA for Splunk****

### OVERVIEW

Overview:	This technology add-on enables key CMX system metrics to be extracted from the CMX application (api interface)

Author: 			Mike Crooks - Block Solutions
App Name: 			TA_cmx_monit – Technology Add-on for extracting CMX system metrics
Version:			v.2.0.1
Vendor Products:	Cisco CMX Application 
Dependencies:		creation of an index to store data

The TA_cmx_monit app provides the key data from a CMX application which allows IT operations to monitor the health of their CMX appliance(s).  Multiple inputs can be used to collect data from multiple CMX instances ensuring that data is all in one place for easy visualisation.

### INSTALLATION AND CONFIGURATION

Testing

This application has only been tested on single server instance. 
This application has been tested on 6.3+
Tests have been run on an apple mac

To install this application, follow either of the mechanisms detailed below;

Install .spl file

Launch Splunk Enterprise
Navigate from the home screen to the apps page via the app settings icon
Click install from file
Browse to the .spl file upload

Manually install

•	Download the .zip file
•	Extract the zip file 
•	Copy contents to splunk/etc/apps
•	Restart Splunk 

Configuring a cmx_monit data input

•	create a dedicated index
•	Navigate to settings -> data inputs -> 
•	Click Add new on the CMX_monit data input row
•	Fill in the form

url:		url of the CMX instance to be monitored
username	username (requires admin rights)
password	password of the admin access
hostname	hostname of the cmx instance


•	click more settings 
•	set Interval (10 seconds has been tested) 
•	Define a sourcetype for the new input (recommended)
•	Select an index to send the data (This add-on creates an index called cmx_monit on install)

##### Scripts and binaries

cmx_api.py

provides the function calls to extract the data from CMX via its api interface

cmx_monit.py

provides the Splunk setup and mechanism to send the data to the index

#### Release notes

Endpoints monitored:

getControllers
Returns controller information

pollCmxServiceStatus
Returns all the services status (RUNNING?)

pollCmxUptime
Returns the system uptime in ms

getHA
Returns the HA configuration information

getLocationLatency
Returns the location latency (should be less than <5000ms)

getNMSPIncomingRate
Returns NMSP rate (should be less than 2500 s)

getApCounts
Returns the AP counts (multiple end points are used to collate this information)

Implemented but not tested and live in code at this time

getAvgMemory
Returns the avg memory usage at this time

getAvgCPU
Returns the avg cpu usage at this time

##### Known issues

Version V.2.0.1 of the <TA_cmx_monit> has the following known issues:

Sometimes the input halts (this may be due to rate limiting on the Cisco sandbox on which this was tested) Restarting Splunk fixes the input.

**Support**

For queries please contact mcrooks@block.co.uk



