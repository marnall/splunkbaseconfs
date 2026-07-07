# FortiMail® App for Splunk®


* FortiMail App for Splunk provides operational and analytical dashboards to enhance visibility on your FortiMail Secure Email Gateway. The goal of this document is to provide installation information for the App.


# Version 1.6.1


# Release Notes


1.6.1: January 2019
- Only updated version reference (1.x.x instead of 1.x) to meet standards. No dashboard update.

1.6: June 2017
- Enhanced both Overview & Tracking dashboards (searches, drilldowns, visualizations)
- Added a python script to decode MIME headers in email subjects (thanks to bkirk - Splunk answers)
- Removed configuration step for internal domain (not needed)

1.5: January 2017
- Updated JavaScript code used to ease multiselect with a 6.5 compliant version (thanks to hobbes3 - GitHub)
- Updated fortimail_virus eventtype to only include infected messages (updated in Splunk_TA_fortimail) (thanks to László)
- XML cleaning

1.4: November 2016
- New Alerts added
- Minor adjustements

1.3: September 2016
- Changes in the Tracking dashboard : both multiselect inputs are re-calculated after a change in the other inputs

1.2: August 2016
- Changes in the recommended inputs

1.1: August 2016
- Minor adjustments

1.0: July 2016
- Initial release


# Prerequisites:


	1 - Deploy FortiMail Add-on for Splunk on your Splunk platform. For distributed environments, FortiMail Add-on for Splunk needs to be deployed on the Search Head as well as on Indexer(s) because it includes transform actions at index-time. Refer to FortiMail Add-on for Splunk documentation for more details.


	2 - Collect syslog events from a FortiMail appliance. In order to forward FortiMail syslog data to a Splunk Indexer or a Heavy Forwarder, please refer to the chapter "Configuring logging to a Syslog server or FortiAnalyzer unit" of editor's admin guide.
	
	
	Note that FortiMail forwards syslog data through UDP on the selected port. It can also forward log data using a secure proprietary protocol called OFTPS but only in order to send it to a FortiAnalyzer or to a FortiManager with the FortiAnalyzer feature enabled.
	
	
	As a result of only being able to use UDP, it is recommended to forward syslog data from FortiMail to a syslog server such as rsyslog or syslog-ng, and then to forward the data to a Splunk Indexer or Heavy Forwarder over TLS.


# Index FortiMail syslog data:

	
	Never mind the chosen path, FortiMail syslog data should be indexed under the sourcetype "fml:log". Configure your Splunk receiving instance to accept FortiMail / syslog server input.

	A sample configuration is provided in FortiMail Add-on for Splunk default directory:

	[Recommended] When FortiMail syslog data is forwarded from a syslog server over TLS:
	
		[tcp-ssl:<port>]
		sourcetype = fml:log
		
		
	[Not recommended] When syslog data is directly forwarded from the FortiMail appliance or VM:
	
		[udp://<FortiMail IP>:514]
		sourcetype = fml:log

		
	It can be used on your Splunk Indexer or Heavy Forwarder.
	
	If needed, please refer to "Get data from TCP and UDP ports" on Splunk Docs.
	
	
	FortiMail syslog data can be indexed in the default main index as well as in a dedicated one. 
	
	If the data is indexed in a dedicated index, this index should be searched by default by the relevant role. This can be configured under Settings: Access controls : Roles : <Role to edit> : FortiMail dedicated index (if any) should be added in "Indexes" as well as in "Indexes searched by default" 

	
# Install FortiMail App for Splunk:


	FortiMail App for Splunk should be installed on your Splunk instance. For distributed environments, it needs to be deployed on the Search Head instance.
	
	To install the App, follow the usual path: Apps : Manage Apps : Install app from file : Browse file : Upload and restart Splunk.
	
	
# Use the "FortiMail - Excessive Messages Sent" alert:


	This alert is available through the "Alerts" view. It has been configured to trigger an alert whenever a user sends more than 100 emails in one hour which behavior can occur when a host is infected.
	
	It has been configured to run every hour and to inspect results from the last hour. It has also been disabled by default. It can be enabled and edited to fit your needs. In order to figure out what threshold of sent emails is appropriate, the average number of email sent by user is given in the panel "Average Messages By Sender/Recipient" of the "Overview" view.


# For any help on this App, contact splunk@nomios.fr




