**** Kaminario K2 App for Splunk Enterprise - README ****


CONTENTS OF THIS FILE
---------------------
   Release Notes
   Introduction
   Requirements
   Recommanded Splunk Enterprise System Configuration
   Download
   Installation
   Configuration
   Application Views
   
* Release Notes
---------------
	-> Vesrion - 1.0, March 2017
	   Initial release.

* Introduction
--------------
	The Kaminario K2 App for Splunk Enterprise leverages the syslog protocol to provide Splunk® Enterprise customers intuitive dashboards and sophisticated analytics for the K2 all-flash array.
	Author - Kaminario.
	
* Requirements
--------------
	-> Splunk Enterprise – version 6.5.2 and later
	-> Kaminario K2 - VisionOS 6.0.2.37 and later
	
* Recommanded Splunk Enterprise System Configuration
----------------------------------------------------
	Same as default Splunk Enterprise minimum requirements

* Download
-----------
	Download the Kaminario K2 App for Splunk Enterprise at https://splunkbase.splunk.com/app/xxx
 
* Installation
---------------
 	->To install the APP using the GUI:
		1.	Log into Splunk Enterprise.
		2.	On the Apps menu, click Manage Apps.
		3.	Click Install app from file.
		4.	In the Upload app window, click Choose File.
		5.	Locate the KaminarioK2 app’s .tar.gz file, and then click Open or Choose.
		6.	Click Upload.
		7.	Click Restart Splunk, and then confirm that you want to restart.

 	->To install the APP using the CLI:
		1.	Put the downloaded file in the $SPLUNK_HOME/etc/apps directory.
		2.	Untar and ungzip your app or add-on using a tool like tar -xvf (on *nix) or WinZip (on Windows).
		3.	Restart Splunk.

* Configuration
----------------
	-> Splunk Enterprise 
		1. Port Listening
			Configure Splunk Enterprise server to get syslog traffic on top of port 514. Using CLI -
			UDP
			 ./splunk add udp 514 -sourcetype syslog
		-OR-
			TCP
			./splunk add tcp 514 -sourcetype syslog
		2. Optional configuration
			.....
	-> Kaminario K2 
	   -> To configure the syslog server using the GUI:
		1.	Log into the K2 GUI using the admin role.
		2.	Go to System > External Configuration.
		3.	Scroll down to the Syslog Servers panel, and then click Add. 
		4.	Insert the following parameters:
			*	Host Name or IP – IP of the Syslog Server (the Splunk Enterprise Server IP).
			*	Port -514, default.
			*	Check the Use TCP checkbox to use TCP syslog transport, otherwise leave unchecked.
			*	Check Report Audit checkbox to send audit data to the Syslog server, otherwise leave unchecked.
			
		-> To configure the Syslog Server using the CLI:
		1.	Log into the K2 CLI using the admin role.
		2.	Configure the Syslog Server on the K2 using the following command:
			system syslog-server-create address=[Syslog Server IP] port=514 report-audit=[True,False] 
			use-tcp=[True,False]
			*	address – Splunk Enterprise servers’ IP as the Syslog Server.
			*	report-audit –True to send audit data to the Syslog Server, otherwise False.
			*	use-tcp - True to use TCP syslog transport, otherwise False.
		3.	Verify the Syslog Server configuration using the following command:
			system syslog-server-show

* Application Views
--------------------
	-> Dashboards
		General Overview
		Capacity
		Events
		Data-Protect
		Auditing
	-> Reports
		All K2 Audit Events
		All K2 Syslog Events
	-> Alerts
		Multiple Failed Logins 
		System Capacity Threshold Crossed

* Support:
----------
To report a problem please refer to the following link for regional toll-free numbers:  http://kaminario.com/support.
	•	Support is provided under the terms and conditions described in Kaminario end user agreement.
	•	Support is provided assuming that no changes were made by the user to the Kaminario K2 App for Splunk.

For further information and optional configuration, please refer to the User Guide, located at $APP_HOME\appserver\static folder.		
		
		
		
		
		
