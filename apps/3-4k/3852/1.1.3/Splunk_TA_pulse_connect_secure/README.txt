# Pulse Connect Secure® Add-on for Splunk®


* Pulse Connect Secure Add-on for Splunk provides CIM compliant field extractions and data enrichment for your Pulse Connect Secure data.

# Version 1.1.3


# Release Notes

1.1.3: April 2020
8.0.0 compatibility

1.1.2: June 2019
- Added extractions for two new fields : header and priority
- Corrected timestamp extraction

1.1.1: January 2019
- Adjusted sourcetype overriding logic by leaving line merging and timestamp extracting parameters in the initial sourcetype only
- removed and unused transforms.conf entry

1.1: January 2018
- Fixed a sample file

1.0: January 2018
	- Initial release


# Install Pulse Connect Secure Add-on for Splunk:


	Deploy Pulse Connect Secure Add-on for Splunk on your Splunk platform. For distributed environments, Pulse Connect Secure Add-on for Splunk needs to be deployed on the Search Head as well as on Indexer(s) or Heavy Forwarder(s) because it includes transform actions at index-time.
	

# Collect syslog events from a Pulse Connect Secure appliance

	
	In order to forward Pulse Connect Secure syslog data to a Splunk Indexer, Heavy Forwarder or syslog server using Splunk format, please refer the following knowledge base article https://docs.pulsesecure.net/WebHelp/Content/PCS/PCS_AdminGuide_8.2/Configuring%20Syslog.htm
	
    
	Among various log format, the Standard (default) format should be chosen.
	
	
	As data is transmitted via UDP only, it is recommended to send it to a syslog server such as rsyslog or syslog-ng, and then to forward it to a Splunk Indexer over TLS.


# Index Pulse Connect Secure syslog data:

	
	Never mind the chosen path, Pulse Connect Secure syslog data should be indexed under the sourcetype "pulse:connectsecure". Configure your Splunk receiving instance to accept Pulse Connect Secure / syslog server input.

	A sample configuration is provided in Pulse Connect Secure Add-on for Splunk default directory:

	[Recommended] When Pulse Connect Secure syslog data is forwarded from a syslog server over TLS:
	
		[tcp-ssl:<port>]
		sourcetype = pulse:connectsecure
		
		
	[Not recommended] When syslog data is directly forwarded from the Pulse Connect Secure appliance or VM:
	
		[udp://<Pulse Connect Secure IP>:514]
		sourcetype = pulse:connectsecure

		
	It can be used on your Splunk Indexer of Heavy Forwarder.
	
	If needed, please refer to "Get data from TCP and UDP ports" on Splunk Docs.
	
	
# Log Samples:


	Do not hesitate to check provided log samples to make sure your indexed data matches data used to build this Add-on.
	
	
# Sourcetypes:


	Besides indexing events under dedicated sourcetype pulse:connectsecure, Pulse Connect Secure Add-on for Splunk will index Web requests under the sourcetype pulse:connectsecure:web.
	
	
# CIM Tags:


	Network Traffic, Network Sessions, Web, Change Analysis & Authentication


# For any help on this App, contact splunk@nomios.fr



