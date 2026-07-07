Forescout Technology Add-on for Splunk
======================================================================

OVERVIEW
------------------------------
This Splunk application is a technology add-on for Forescout App for Splunk.

* Author - fs_splunk_app@forescout.com
* Version - 3.0.5
* Build - 1
* Creates Index - False
* Source type - fsctcenter_json, fsctcenter_avp
* Compatible with:
  Splunk Enterprise version: 7.x, 8.x, and 9.x
  Splunk Cloud Enterprise version: 7.2.x, 8.0.x, 8.1.x, and 8.2.x
  Common Information Model: 4.18
  OS: Platform independent
* This application is a Technology Add-on for Forescout App for Splunk (forescout_app).
  
 
RELEASE NOTES
------------------------------
*Version 3.0.3
  Support Macros in Splunk Search Head Cluster

*Version 3.0.2
  Supports adding the {in-group} tag to Splunk Message
  Macros in event types are removed for better distributed Splunk Deployment
  Fixed syntax errors defined in props.conf
  Supports Python 3

*Version 3.0
  Supports CIM modelling
  Supports Splunk SHC Clustering

* Version 2.9.2_2
  App rewritten in Javascript

* Version 2.9.2
  Supports App migration from python 2 to python 3

* Version 2.9.1
  Support communication between Splunk server and Forescout CounterACT via IPv6 address.
  Bug fixes.
  
* Version 2.7.0
  The setup page now allows the user to specify an index from which 'forescout_app' and 'TA-forescout_response' will read their data.
  Before making any edits on the setup page, the user no longer needs to manually delete the 'passwords.conf' file.
  All 'TA-forescout' setup logs are logged in a separate file named 'TA-forescout_setup.log'.
  Bug fixes.

* Version 2.6.0
  Documentation changes and version upgrade.
  Bug fix for Setup page endpoint conflicting stanza.

* Version 2.5.1
  Removed unnecessary README file from bin folder.
  Removed unused imports from python scripts.
  Commented [udp://515] stanza from inputs.conf to comply with Splunk Cloud Certification.
  Commented [tcp://515] stanza from inputs.conf to comply with Splunk Cloud Certification.
  Removed Communications to CounterACT settings block from setup.xml.
  Modified fsctsetup.conf to give default value 1 to usessl and verifycert parameters.

* Version 2.5.0
  Extracted new fields.


SUPPORT
------------------------------
* Contact information for reporting an issue:
  fs_splunk_app@forescout.com


DOWNLOAD
------------------------------
* Download the ForeScout Technology Add-on for Splunk from Splunkbase - https://splunkbase.splunk.com/app/3382/


USING SAMPLE DATA
-------------------------------------
* This app contains sample data in "samples" folder and eventgen configuration which can be used to test visualization dashboards of ForeScout App for Splunk application by populating sample data using SA-Eventgen app. Sample event data will be generated in index=fsctcenter by default.
