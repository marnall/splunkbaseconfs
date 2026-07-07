# Trend® IMSVA Add-on for Splunk®


Trend IMSVA Add-on for Splunk provides CIM compliant field extractions and data enrichment for your Trend InterScan Messaging Security (IMSVA) data.


# Version 1.0.0


# Release Notes


1.0.0: October 2019

- Initial release


# Trend IMSVA data


The add-on provides field extractions and data enrichment for both 'Policy events' and 'Message tracking' IMSVA data.

'Policy events' provide details on the filtering process while 'Message tracking' data provides insight on the final action taken by the virtual appliance.


# Collect Trend IMSVA data


While IMSVA supports syslog since version 9.1 this add-on has been actually developed before syslog option was available and relies on having the Splunk Universal Forwarder deployed on the IMSVA and directly monitoring the files.

Although having the Universal Forwarder deployed on the virtual appliance worked pretty well for us but you have to consider that it might not an option the vendor would recommend and even less support.

So far, we did not have the chance to test syslog option.


# Add-on deployment


Install the Add-on on your Splunk platform.

For distributed environments, the Add-on needs to be deployed on the on Indexer(s) as it includes parsing configuration parameters.


# Index IMSVA data


IMSVA data should be indexed under both 'trend:imsva:polevt' and 'trend:imsva:msgtra' sourcetypes using these monitoring stanzas:

	[monitor:///opt/trend/imss/log/msgtra.imss.*]
	sourcetype = trend:imsva:msgtra
	index = <index>

	[monitor:///opt/trend/imss/log/polevt.imss.*]
	sourcetype = trend:imsva:polevt
	index = <index>


# Log Sample


Do not hesitate to check provided log sample to make sure your indexed data matches data used to build this Add-on.


# Additional notes


With support's help, we did our best to understand and extract as many fields as we could but as the logging format is not fully documented, there might be a few field extractions missing.

If you have more info on the missing fields, please share with us and we will improve the add-on.

If you opt for the syslog option, this add-on is not compatible yet but feel free to provide an anonymized sample so we can work on that.


# For any help or suggestion on this App, contact d2si-spk [at] protonmail.com



