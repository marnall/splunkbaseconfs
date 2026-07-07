# FortiMail® Add-on for Splunk®


* FortiMail Add-on for Splunk provides CIM compliant field extractions and data enrichment for your FortiMail Secure Email Gateway data. This Add-on can be used on his own in order to normalize your email data. It also works in conjunction with FortiMail App for Splunk in order to profit from configured dashboards. The goal of this document is to provide installation information for the Add-on.


# Version 1.7.1


# Release Notes


1.7.1: January 2019
- Fixed sourcetype overriding logic by moving line merging and timestamp extracting parameters to base sourcetype

1.7: January 2018
- Minor CIM fields adjustments

1.6: June 2017
- Added delay calculation
- Corrected a few CIM field extractions
- Simplified CIM tags

1.5: January 2017
- Added TIME_FORMAT definition for better efficiency

1.4: January 2017
- Updated fortimail_virus eventtype to only include infected messages (Thanks to László)

1.3: November 2016
- 6.5 ready

1.2: August 2016
- Changes in the recommended inputs

1.1: August 2016
- Field extraction adjustments

1.0: July 2016
- Initial release


# Install FortiMail Add-on for Splunk:


	Deploy FortiMail Add-on for Splunk on your Splunk platform. For distributed environments, FortiMail Add-on for Splunk needs to be deployed on the Search Head as well as on Indexer(s) because it includes transform actions at index-time.
	

# Collect syslog events from a FortiMail appliance

	
	In order to forward FortiMail syslog data to a Splunk Indexer or a Heavy Forwarder, please refer to the chapter "Configuring logging to a Syslog server or FortiAnalyzer unit" of editor's admin guide.

	
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

		
	It can be used on your Splunk Indexer of Heavy Forwarder.
	
	If needed, please refer to "Get data from TCP and UDP ports" on Splunk Docs.
	
	
	FortiMail syslog data can be indexed in the default main index as well as in a dedicated one. 
	
	If the data is indexed in a dedicated index, this index should be searched by default by the relevant role. This can be configured under Settings : Access controls : Roles : <Role to edit> : FortiMail dedicated index (if any) should be added in "Indexes" as well as in "Indexes searched by default" 


# Sourcetypes:


	From the original fml:log sourcetype, FortiMail Add-on for Splunk will index events under dedicated sourcetypes based on their type:
	
	Statistics: sourcetype = fml:statistics
	
	Event: sourcetype = fml:event
	
	Spam: sourcetype = fml:spam
	
	Virus: sourcetype = fml:virus
	
	Encryption: sourcetype = fml:encrypt
	
# CIM Tags:


	Email & Authentication


# For any help on this App, contact splunk@nomios.fr





