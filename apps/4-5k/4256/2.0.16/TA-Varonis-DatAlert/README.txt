------------
Varonis, Ltd.
------------
 
CONTENTS OF THIS FILE
*********************
-Overview
-Download
-Support
-Documentation
-License
-Release Notes
 
 
OVERVIEW
*********************
The Varonis Technology Add-on (TA) for Splunk(R) enables integrating the Varonis DatAlert functionality into Splunk Enterprise. The TA, together with the Varonis App for Splunk provides field extractions and dashboards that enable you to locate notable Varonis alerts directly from the Splunk user interface and then drill down into Varonis DatAlert to get additional insights into the alert and the context in which it was generated. Also, field extractions assist users in querying and visualizing Varonis alerts using Splunk Enterprise.
 
Varonis App and TA are Splunk CIM compliant which enables correlating the Varonis alerts with other events collected by Splunk Enterprise as well is incorporating Varonis alerts in Splunk Enterprise Security (ES).
 
This TA incorporated parts of "CEFUtils - Common Event Format Extraction Utilities" by Igor Sher (https://splunkbase.splunk.com/app/487/).
 
 
DOWNLOAD
*********************
The Varonis Technology Add-on for Splunk and Varonis App for Splunk can be downloaded at:
https://www.varonis.com/products/splunk-app/
 
 
SUPPORT
*********************
For information on how to contact support, refer to the Varonis support page at:
https://www.varonis.com/services/support
 
 
DOCUMENTATION
*********************
A complete user guide, containing installation, configuration, and app usage instructions for both the app and the Technology Add-on, can be found here:
https://www.varonis.com/products/splunk-app/user-guide/
 
 
LICENSE
*********************
Please refer to LICENSE.TXT at:
https://www.varonis.com/products/splunk-app/splunk-app-license/
 
 
RELEASE NOTES
*********************
New for version 2.0.8:
* Bugs fixing

New for version 2.0.7:
* Bugs fixing

New for version 2.0.6:
* Updated static icons

New for version 2.0.5:
*The following changes have been made to the Varonis mapping of Splunk Common Information Model (CIM) data models:
1) Fixed missing support for Cloud admin 

New for version 2.0.4:
*The following changes have been made to the Varonis mapping of Splunk Common Information Model (CIM) data models:
1) Updated CIM mapping with the Alerts data model enables focused search for Varonis alerts.
2) New Varonis threat models are now supported.
3) The Ids data model is no longer used.


New for version 1.2:
* Fixed issues identified by AppInspect:
** Renamed eventtype DNS_cache_poisoning_(birthday_attack) to DNS_cache_poisoning_birthday_attack to be compliant
** Removed empty row from lookup varonis_outcome_type_lookup.csv 
** Removed emtpy row from lookup varonis_outcome_action_lookup.csv


New for version 1.1:
* Hid the TA from the App Navigation on the Splunk main page

New for version 1.0:
* Added support for Splunk CIM
* Field Extractions and Knowledge Objects have been moved from our App to this Technology Add-On
