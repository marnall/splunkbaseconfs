##Readme for the Tripwire Enterprise App for Splunk Enterprise
##Author: Fortra, LLC
##Version: 3.4.0

#PREREQUISITES:
* Splunk 9.2.0 or above
* Tripwire Enterprise 9.2.0 or above

# CHANGES AND NEW FEATURES VERSION 3.4.0

**Changes to Tripwire Enterprise App**

* Added tagging filter support for SCM data dashboards and waivers.
* Modified searches to utilize Splunk lookups and avoid joins, resulting in improved scalability and performance for clustered environments.

**Changes to Tripwire Enterprise App**

* The app now requires the Tripwire Enterprise Data Adapter to be enabled.
* You must install the Universal Forwarder on the TE console.
* Installation of the 3.4.0 Tripwire Enterprise App on both the Splunk Universal Forwarder and the Splunk Enterprise is required.

#DOCUMENTATION:
- Link to project's website: https://www.tripwire.com/resources/datasheets/tripwire-enterprise/splunk
- For detailed documentation, including installation and configuration instructions, please see the included "TripwireEnterpriseSplunk.pdf" file