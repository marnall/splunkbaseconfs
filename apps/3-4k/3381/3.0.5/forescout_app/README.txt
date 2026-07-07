Forescout App for Splunk
======================================================================

OVERVIEW
-----------------------------------
The Forescout App for Splunk provides visibility and helps to monitor Forescout CounterACT endpoints, identify threats, take CounterACT actions on each such incidents and track the responses coming from CounterACT.

* Author - fs_splunk_app@forescout.com
* Version - 3.0.4
* Build - 1
* Creates Index - False
* Uses Source type - fsctcenter_json, fsctcenter_avp, counteract_alerts, counteract_orig_event and scheduler.
* Prerequisites - This application is dependent on ForeScout Technology Add-on for Splunk (TA-forescout) and ForeScout Adaptive Response Add-on for Splunk  (TA-forescout_response).
* Compatible with:
  Splunk Enterprise version: 7.x, 8.x, and 9.x
  Splunk Cloud Enterprise version: 7.2.x, 8.0.x, 8.1.x, and 8.2.x
  Common Information Model: 4.18
  OS: Platform independent


OPEN SOURCE COMPONENTS AND LICENSES
-----------------------------------
* Some of the components included in Forescout App for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.
  jQuery version 2.1.0 http://jquery.com/ (LICENSE https://github.com/jquery/jquery/blob/master/LICENSE.txt)
  Underscore JS version 1.6.0 http://underscorejs.org (LICENSE https://github.com/jashkenas/underscore/blob/master/LICENSE)
  Require JS version 2.1.15 http://github.com/jrburke/requirejs (LICENSE https://github.com/requirejs/requirejs/blob/master/LICENSE)


RELEASE NOTES
-----------------------------------
*Version 3.0.3
  Support Macros in Splunk Search Head Cluster

*Version 3.0.2
  Supports Jquery 3.5+

*Version 3.0.1
  Supports adding the {in-group} tag to Splunk Message
  Macros in event types are removed for better distributed Splunk Deployment
  Fixed syntax errors defined in props.conf
  Supports Python 3

*Version 3.0
  Supports CIM modelling
  Supports Splunk SHC Clusterinh


* Version 2.9.2
  Supports App migration from python 2 to python 3

* Version 2.9.1
  Support communication between Splunk server and Forescout CounterACT via IPv6 address.
  Bug fixes.

* Version 2.7.0
  Updated all dashboards to work on batched messages received from the CounterACT Splunk Module.
  On every Splunk service restart, the 'forescout_app' now writes a message to the bulletin board indicating if the index fields from 'TA-forescout' could be read successfully or not.
  All 'forescout_app' app startup logs are logged in a separate file named 'forescout_app_init.log'.
  Bug fixes.

* Version 2.6.0
  Documentation changes and version upgrade.

* Version 2.5.1
  Removed empty README folder.
  Replaced Curly Singly Quotes with Non-Curly Single Quotes in app.conf description field.
  Added used Open Source Component Name, Version, URL and License URL in README.txt file.

* Version 2.5.0
  Added new dashboards.


SUPPORT
-----------------------------------
* Contact information for reporting an issue:
  fs_splunk_app@forescout.com


DOWNLOAD
------------------------------
* Download the Forescout App for Splunk from Splunkbase - https://splunkbase.splunk.com/app/3381/


SAVED SEARCHES
------------------------------
* This app contains saved search queries related to visualization dashboards for Forescout CounterACT.