# Barracuda WAF/ADC® Add-on for Splunk®


* Barracuda WAF/ADC Add-on for Splunk provides CIM compliant field extractions and data enrichment for your Barracuda WAF/ADC data.


# Version 1.0.2


# Release Notes


1.0.1: January 2019
- Minor fixes to pass AppInspect

1.0.1: January 2019
- Adjusted sourcetype overriding logic by leaving line merging and timestamp extracting parameters in the initial sourcetype only

1.0: November 2017
- Initial release


# Install Barracuda WAF/ADC Add-on for Splunk:


	Deploy Barracuda WAF/ADC Add-on for Splunk on your Splunk platform. For distributed environments, Barracuda WAF/ADC Add-on for Splunk needs to be deployed on the Search Head as well as on Indexer(s) because it includes transform actions at index-time.
	

# Collect syslog events from a Barracuda WAF/ADC appliance

	
	In order to forward Barracuda WAF/ADC syslog data to a Splunk Indexer , Heavy Forwarder or syslog server using Splunk format, please refer the following knowledge base article https://campus.barracuda.com/product/webapplicationfirewall/doc/4259935/how-to-configure-syslog-and-other-logs/
	
	
	As data is transmitted via UDP only, it is recommended to send it to a syslog server such as rsyslog or syslog-ng, and then to forward it to a Splunk Indexer over TLS.


# Index Barracuda WAF/ADC syslog data:

	
	Never mind the chosen path, Barracuda WAF/ADC syslog data should be indexed under the sourcetype "barracuda:log". Configure your Splunk receiving instance to accept Barracuda / syslog server input.

	A sample configuration is provided in Barracuda WAF/ADC Add-on for Splunk default directory:

	[Recommended] When Barracuda syslog data is forwarded from a syslog server over TLS:
	
		[tcp-ssl:<port>]
		sourcetype = barracuda:log
		
		
	[Not recommended] When syslog data is directly forwarded from the Barracuda appliance or VM:
	
		[udp://<Barracuda IP>:514]
		sourcetype = barracuda:log

		
	It can be used on your Splunk Indexer of Heavy Forwarder.
	
	If needed, please refer to "Get data from TCP and UDP ports" on Splunk Docs.
	
	
# Log Samples:


	Do not hesitate to check provided log samples to make sure your indexed data matches data used to build this Add-on.
	
	
# Sourcetypes:


	From the original barracuda:log sourcetype, Barracuda WAF/ADC Add-on for Splunk will index events under dedicated sourcetypes based on their type:
	
	Web Application Firewall: sourcetype = barracuda:waf
	
	Reverse Proxy: sourcetype = barracuda:web
	
	Network Firewall: sourcetype = barracuda:firewall
	
	System: sourcetype = barracuda:system
	
	Audit: sourcetype = barracuda:audit
	
	
# CIM Tags:


	Intrusion Detection, Web, Network Traffic, Change Analysis & Authentication


# For any help on this App, contact splunk@nomios.fr




