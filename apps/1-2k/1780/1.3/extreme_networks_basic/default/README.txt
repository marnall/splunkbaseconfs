Extreme Networks EXOS for Splunk
===========================

---- Description ----

Operational intelligence for Extreme Networks
hardware running EXOS; dashboards for network monitoring
and troubleshooting.

---- Current Version ----
#Splunk version: 6.x
#App version: 1.2
#Last modified: Jan 7, 2015
#Author: William Lee, Extreme Networks

---- Support ----
For issues, bug reports, or feature suggestions, please email: splunk@extremenetworks.com

---- What's New in this Version ----
Added odometer readings to model details.

---- Installation ----
1) Unpack tar file into $SPLUNK_HOME/etc/apps/ -- ex: tar -xzvf enbasic_v1.tar.gz -C /opt/splunk/etc/apps/
2) Restart Splunk

---- Additional Setup ----
For this app to work properly, you will need to make the following changes:
1) Create an index named 'extnet' (Settings->Indexes in SplunkWeb). More details regarding this can be found at: 
		http://docs.splunk.com/Documentation/Splunk/6.0.3/Indexer/Setupmultipleindexes#Create_and_edit_indexes
2) Create a TCP data input for your switch data (Settings->Data inputs in SplunkWeb). 
	a. Set a TCP port -- you will later need to configure your switches to send tech support reports on this port. Our examples below use Port 6514.
	b. Under "Source name override" enter 'en-switch'.
	c. Under the "Source type" heading, "Set sourcetype" as Manual. Enter 'tcp-raw' in the "Source type" field. 
	d. Under the "More settings" option select 'extnet' on the "Index" dropdown.
	e. Click "Save"
4) Restart Splunk.
5) Start sending data!

---- A Note About Your Data ----
EXOS currently supports automatically reporting tech support data to Extreme Networks. This feature is off by default, but turning on reporting via the commands below will enable it. 
****IF YOU DO NOT WANT TO SEND EXTREME NETWORKS YOUR TECH SUPPORT REPORTS FOLLOW THE INSTRUCTIONS IN STEP 6 BELOW****
All data sent to Extreme Networks will only be used internally for research purposes (e.g.  EXOS versions and features being used). Extreme Networks will not contact you regarding this data, use this data for remote access, or release the data to third parties. Customers with active service contracts on Extreme Networks switches may choose to permit our Technical Support Engineers to access this data for troubleshooting network issues on a case-by-case basis.


---- EXOS Requirements and Configuration for Using the Extreme Networks Splunk App ----

-- General Requirements --
1)	A Splunk Server running version 6.0 or greater with the Extreme Networks Splunk App installed.
2)	An Extreme Networks EXOS switch with network access to the Splunk server hosting the app.
	a.	To send proactive tech-support reports to Extreme Networks, the switch will need to be able to access the Internet, specifically 12.38.14.200, TCP port 800.
3)	An Extreme Networks EXOS switch running software version 15.4 or greater.

-- EXOS Configuration Commands --
1)	debug tech-support configure max-collectors 2
	Note: This requirement will be removed in a future EXOS release.

2)	
	a.	(Less common) If you’re using the mgmt port interface to communicate to the server, use this command add the collector: 
			configure tech-support add collector [hostname | ip_address] tcp-port <port#> {ssl [on | off]}
	b.	(More common) If you’re using an interface in one of the user VRs, follow these instructions:
			configure tech-support add collector [hostname | ip_address] tcp-port <port#> {vr vr_name} {from source_ip_address} {ssl [on | off]}
	Our demo setup uses TCP port 6514, which is for Syslog over TLS (RFC 5425).  See: 
			http://docs.splunk.com/Documentation/Splunk/latest/Security/ConfigureSplunkforwardingtousethedefaultcertificate
	for information on enabling SSL/TLS (not required).
	Example:  configure tech-support add collector 192.168.1.100 tcp-port 6514 vr VR-Default from 192.168.1.1 ssl off
	Due to PD4-4385171973 (only in 15.4.1), you'll need run the same command again, but without the "add" command.  This serves to reconfigure the addition.  This bug will be fixed in future EXOS releases.

3)	Validate the proper addition of the collector with the 'show tech-support collector command'.  At this point, the output should look similar to this:
		* X440-24t-10G.8 # show tech-support collector 
		Tech Support Collector:       Enabled
		Max Collectors:               2

		Report Collector:             192.168.1.100
			TCP Port:                 6514
			Virtual Router:           VR-Default	<- This should match your chosen configuration from above
			Source IP Addr:           192.168.1.1
			SSL:                      Off
			Report Mode:              Automatic
			Report Data Set:          Summary
			Report Frequency:         Bootup
			Last Report:              Not Generated
			Next Cyclic Report:       Not Scheduled
			Next One Time Report:     Not Scheduled
	You can also use the 'show configuration techSupport' command to verify what you have entered was accepted.

4)	Once the collector is added, you can configure the report frequency.  Here’s the options:
		* X440-24t-10G.19 # configure tech-support collector 192.168.1.100 frequency 
		  bootup          Send status report when the switch boots up (Default on)
		  daily           Send status report once a day (Default off)
		  error-detected  Send status report when a critical severity event is logged (Default off)

5)	After the frequency is determined, you can configure the data-set.  This is the set of information used in the tech-support report.  The default is “detail” if SSH/SSL is enabled.  “Summary” is used otherwise.
		* X440-24t-10G.19 # configure tech-support collector 192.168.1.100 data-set 
		  detail          Output of 'show tech-support all'
		  summary         Output of 'show tech-support <area>' for area general, config, log, VLAN, and EPM

6)	If you want to disable the default configuration of reporting to Extreme Networks but want to keep your own internal reporting, set the frequency of the external collector to “manual” with this command:
		configure tech-support collector 12.38.14.200 report manual

-- Testing the Configuration --
You can manually run the tech-support collector at any time from the CLI.  There’s several options:
		* X440-24t-10G.20 # run tech-support report 
		  <cr>            Execute the command
		  cancel          Cancel scheduled report
		  collector       Report collector (Default all collectors)
		  in              Schedule to run report in some hours
		  now             Run report immediately (Default)
For this example, we’ll test the collector that we just configured above.  This activity takes about one minute, depending on system load and network speed.
		* X440-24t-10G.21 # run tech-support report collector 192.168.1.100 
		Connecting to 192.168.1.100:6514 with SSL disabled...
		Collector connected successfully.
		Generating summary report for 192.168.1.100:6514................................................................
		Report generated successfully.
		Sending report to 192.168.1.100:6514...
		Report sent successfully

------ Credits ------
Additional queries, data collection, and support by Cory Liverman, Extreme Networks
Testing, hardware support, and design by Drew Claybrook and Scott Groff, Extreme Networks

