Forescout Adaptive Response Add-on for Splunk
======================================================================

OVERVIEW
------------------------------
This Splunk application is CounterACT module for Splunk Enterprise Security Suite.

* Author - fs_splunk_app@forescout.com
* Version - 3.0.7
* Build - 1
* Creates Index - False
* Uses Source type - fsctcenter_json, fsctcenter_avp, counteract_alerts, counteract_orig_event and scheduler.
* Prerequisites - This application is dependent on Forescout Technology Add-on for Splunk (TA-forescout).
* Compatible with:
  Splunk Enterprise version: 7.x, 8.x, and 9.x
  Splunk Cloud Enterprise version: 7.2.x, 8.0.x, 8.1.x, and 8.2.x
  Common Information Model:           4.18
  OS: Platform independent
* This application is a Technology Add-on wth Adaptive Response for Forescout App for Splunk (forescout_app).


OPEN SOURCE COMPONENTS AND LICENSES
-----------------------------------
* Some of the components included in Forescout Adaptive Response Add-on for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.
  requests 2.3.0 http://docs.python-requests.org/ (LICENSE https://github.com/kennethreitz/requests/blob/master/LICENSE)
  
  
RELEASE NOTES
------------------------------
*Version 3.0.3
  Support Macros in Splunk Search Head Cluster

*Version 3.0.2
  Added the trigger stanza in app.conf to maintain cloud compatibility

*Version 3.0.1
  Supports adding the {in-group} tag to Splunk Message
  Macros in event types are removed for better distributed Splunk Deployment
  Fixed syntax errors defined in props.conf
  Supports Python 3

*Version 3.0
  Supports CIM modelling
  Supports Splunk SHC Clustering

* Version 2.9.2
  Supports App migration from python 2 to python 3

* Version 2.9.1
  Support communication between Splunk server and Forescout CounterACT via IPv6 address.
  Bug fixes.
  
* Version 2.7.0
  Updated all saved searches to work on batched messages received from the CounterACT Splunk Module.
  Added a new 'Test alert' that would look for test events sent by the CounterACT Splunk Module and send test alerts to the CounterACT IP address/hostname configured in the 'TA-forescout' app's setup page.
  On every Splunk service restart, the 'TA-forescout_response' app now writes a message to the bulletin board indicating if it CounterACT actions could be retrieved successfully or not.
  On every Splunk service restart, the 'TA-forescout_response' app now writes a message to the bulletin board indicating if the index fields from 'TA-forescout' could be read successfully or not.
  All 'TA-forescout_response' app startup logs are logged in a separate file named 'TA-forescout_response_init.log'.
  Bug fixes.

* Version 2.6.0
  Fixed storage passwords retrieval issue by restricting the passwords list from TA-forescout add-on only.
  Documentation changes and version upgrade.

* Version 2.5.1
  Added used Open Source Component Name, Version, URL and License URL in README.txt file.
  Action python scripts code optimizations.
  Modified monitor/batch path for Modular Action events to application's local folder.
  Used Splunk API to get management port URL instead of hardcoded localhost.
  Removed potential credentials leak from being logged in exceptions.

* Version 2.5.0
  Added support for Splunk Enterprise Security Module for Forescout ConterACT.


SUPPORT
------------------------------
* Contact information for reporting an issue:
  fs_splunk_app@forescout.com


DOWNLOAD
------------------------------
* Download the Forescout Adaptive Response Add-on for Splunk from Splunkbase - https://splunkbase.splunk.com/app/3383/


SAVED SEARCHES
------------------------------
* This app contains saved search queries related to Splunk Adaptive Response Framework. Disable these saved searches in case this feature is not used.