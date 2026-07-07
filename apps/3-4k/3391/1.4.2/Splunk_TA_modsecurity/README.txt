# ModSecurity® Add-on for Splunk®


* ModSecurity Add-on for Splunk provides CIM compliant field extractions and data enrichment for your ModSecurity Web Application Firewall data. This Add-on can be used on his own to normalize your Web Application Firewall data. To profit from configured dashboards it can also be used in conjunction with ModSecurity App for Splunk. The goal of this document is to provide installation information for the Add-on.


# Version 1.4.2


# Release Notes


1.4.2: January 2019
- Minor fixes to pass AppInspect

1.4.1: January 2019
- Removed an unused entry from transforms.conf

1.4: October 2017
- Added support for alternate ModSecurity alerts
		
1.2: March 2017	
- Corrected fields extractions for Intrusion Detection event datasets
- Added fields extractions for Web event datasets

1.1: January 2017
- Added TIME_FORMAT definition for greater efficiency

1.0: November 2016
- Initial release
		

# Install ModSecurity Add-on for Splunk:


	Deploy ModSecurity Add-on for Splunk on your Splunk platform. For distributed environments, ModSecurity Add-on for Splunk needs to be deployed on the Search Head as well as on Indexer(s).
	
	
# Enable audit logging in ModSecurity


	ModSecurity audit logs need to be enabled and several resources describe the process. One of them is the reference manual hosted on GitHub: https://github.com/SpiderLabs/ModSecurity/wiki/Reference-Manual#secauditengine


# Collect ModSecurity audit logs


	Your Splunk Universal Forwarder hosting ModSecurity should be configured to monitor ModSecurity's audit logs and forward it to your Splunk Indexer or Heavy Forwarder.


	To achieve this, a local inputs.conf should be manually configured or deployed via a Deployment Server to monitor modsec_audit.log file which default location is /var/log/httpd/modsec_audit.log


	A sample configuration is provided in the Add-on README directory:


	[monitor:///var/log/httpd/modsec_audit.log]	
	sourcetype = modsec:audit


	If needed, please refer to "Monitor files and directories using the Universal Forwarder" on Splunk Docs.


	ModSecurity data can be indexed in the default main index as well as in a dedicated one.


	If the data is indexed in a dedicated index, this index should be searchable by default by the relevant role. This can be configured under Settings: Access controls : Roles : <Role to edit> : ModSecurity dedicated index (if any) should be added in "Indexes" as well as in "Indexes searched by default".


# Sourcetype:


	The configured sourcetype is "modsec:audit"


# CIM Tags:


	Intrusion Detection & Web


# For any help on this App, contact splunk@nomios.fr



