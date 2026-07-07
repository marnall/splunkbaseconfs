The Sidewinder Add-on for Splunk adds the required knowlegde objects to make logs generated in the Sidewinder Log Format CIM compliant for use with the Splunk App for Enterprise Security and other CIM reliant apps.

This TA should be installed on any indexers collecting firewall data as well as the search head(s) (if deployed in a distributed environment) and requires all Sidewinder event data to use the "sidewinder" sourcetype when indexed. This allows a transform within the TA to write the "host" field based on the firewall hostname in the event data.

***NOTE: This TA has only been tested with SecureOS v8

Version:		1.0.0
Support:		Splunk Answers Only
System Requirements:	Architecture Independent
Prerequisites:		None
