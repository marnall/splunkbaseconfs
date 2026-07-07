Technology Add-on for Stackdriver Windows Security Event Logs
======================================================================

OVERVIEW
------------------------------
This add-on provides CIM compliant field extractions for Windows event logs sourced from Stackdriver, for Windows endpoints hosted in Google Cloud Platform.  With the default Stackdriver Windows agent configuration, the entire Windows security event is stored inside a single field (jsonPayload.message).  This add-on provides the extractions necessary to clean and parse the content of this field into the appropriate key=value pairs.

* Author - Tony Marrazzo
* Version - 1.0.0
* Build - 1
* Creates Index - False
* Compatible with:
    - Splunk Enterprise version: 6.5.x, 6.6.x, 7.0.x, and 7.1.x
    - OS: Platform independent
* Dependencies:
	- Splunk Add-on for Windows version 5.0.1
	- Splunk Add-on for Google Cloud Platform version 1.1.x or greater

SETUP
------------------------------
* Pre-installation Requirements:
    * Stackdriver logging agents have been deployed to your Google Cloud Platform Windows hosts
    * The Splunk Add-on for Google Cloud Platform has been installed and configured to send stackdriver endpoint logs into your Splunk environment
    * The Splunk Add-on for Windows has been installed and configured on your search head.
    * A unique source or sourcetype has been configured for specifically identifying Windows endpoint logging from amongst other pub/sub subscriptions
    * For more information regarding Google Cloud Platform inputs configurations, please see the documentation for the Splunk Add-on for Google Cloud Platform - http://docs.splunk.com/Documentation/AddOns/released/GoogleCloud/About
* Before installing the TA onto the Search Head:
	* Extract the TA and edit line 4 of props.conf to the appropriate source or sourcetype used for stackdriver endpoint logs in your environment.  
		* An example has been provided for you using the default Google Cloud Platform pub sub sourcetype - google:gcp:pubsub:message.  For speed and efficiency, you will want to specify a source or sourcetype which only contains stackdriver windows endpoint logs, and replace the value in line 4.
* On Splunk Search Head:
    * On Splunk Search head, install the TA

SUPPORT
------------------------------
* Contact information for reporting an issue:
  tony.marrazzo@datahunters.com
