OVERVIEW

The EMC VNX App for Splunk Enterprise allows Splunk Enterprise administrators to gain insight into VNX Array inventory and performance data.

	Author: Dean Jackson
	Version: 1.2
	Array compatibility: EMC VNX1 or VNX2 arrays
	Splunk compatibility: 6.4, 6.5
	OS: platform independent

SUPPORT

	Contact via email: dean.jackson@dell.com
	Hours: Weekday business hours (Australia, East Coast)

REQUIREMENTS

	Splunk version 6.4, 6.5
	Splunk Treemap 1.1.1 
		https://splunkbase.splunk.com/app/3118/
	Splunk Add-On for EMC VNX 1.2.0
		https://splunkbase.splunk.com/app/1836/

INSTALLATION

1. The app only needs to be installed on the search heads, and requires no configuration.
2. Ensure the the Splunk Add-on for EMC VNX has been installed and configured on a forwarder. See: http://docs.splunk.com/Documentation/AddOns/latest/EMCVNX/Description
3. Ensure that a VNX index has been setup on the indexers receiving from the forwarder.
4. Ensure that the Splunk Treemap visualisation has been installed on the search head.

NOTES

Please note legacy installations of Splunk add-on for VNX may have a dedicated index named "vnx". This app now leverages macros for index references, please change macros.conf 
to appropriate index you use, as the default is now set to main.
