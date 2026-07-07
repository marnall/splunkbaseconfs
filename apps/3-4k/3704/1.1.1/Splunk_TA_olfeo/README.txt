# Olfeo® Add-on for Splunk®


* Olfeo Add-on for Splunk provides CIM compliant field extractions and data enrichment for your Olfeo data.


# Version 1.1.1


# Release Notes


1.1.1: January 2019
- Adjusted sourcetype overriding logic by leaving line merging and timestamp extracting parameters in the initial sourcetype only

1.1: October 2017
- Minor adjustement

1.0: September 2017
- Initial release


# Install Olfeo Add-on for Splunk:


	Deploy Olfeo Add-on for Splunk on your Splunk platform. For distributed environments, Olfeo Add-on for Splunk needs to be deployed on the Search Head as well as on Indexer(s) because it includes transform actions at index-time.
	

# Collect syslog events from a Olfeo appliance

	
	In order to forward Olfeo syslog data to a Splunk Indexer, Heavy Forwarder or syslog server, please refer the following knowledge base article https://support.olfeo.com/en/kb/article/2560
	
	
	As data is transmitted via UDP only, it is recommended to send it to a syslog server such as rsyslog or syslog-ng, and then to forward it to a Splunk Indexer over TLS.


# Index Olfeo syslog data:

	
	Never mind the chosen path, Olfeo syslog data should be indexed under the sourcetype "olfeo". Configure your Splunk receiving instance to accept Olfeo / syslog server input.

	A sample configuration is provided in Olfeo Add-on for Splunk default directory:

	[Recommended] When Olfeo syslog data is forwarded from a syslog server over TLS:
	
		[tcp-ssl:<port>]
		sourcetype = olfeo
		
		
	[Not recommended] When syslog data is directly forwarded from the Olfeo appliance or VM:
	
		[udp://<Olfeo IP>:514]
		sourcetype = olfeo

		
	It can be used on your Splunk Indexer of Heavy Forwarder.
	
	If needed, please refer to "Get data from TCP and UDP ports" on Splunk Docs.
	
	
# Sourcetypes:


	Proxy: sourcetype = olfeo
	
	System: sourcetype = olfeo:system
	
	Filtering: sourcetype = olfeo:filtering
	

# CIM Tags:


	Web


# For any help on this App, contact splunk@nomios.fr



