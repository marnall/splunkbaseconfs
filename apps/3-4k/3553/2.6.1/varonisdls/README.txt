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
The Varonis App for Splunk(R) enables integrating the Varonis DatAlert functionality into Splunk Enterprise. The App, together with the Varonis Technology Add-on (TA) for Splunk provides field extractions and dashboards that enable you to locate notable Varonis alerts directly from the Splunk user interface and then drill down into Varonis DatAlert to get additional insights into the alert and the context in which it was generated. Also, field extractions assist users in querying and visualizing Varonis alerts using Splunk Enterprise.
 
Varonis App and TA are Splunk CIM compliant which enables correlating the Varonis alerts with other events collected by Splunk Enterprise as well is incorporating Varonis alerts in Splunk Enterprise Security (ES).
 
 
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

New for Version 2.6.0:
*Updated static icons

New for Version 2.5.0:
*The application is now compatible with the Splunk cloud.

New for Version 2.4.0:
*The new dashboard is compatible with JavaScript ES9.
*The application is enhanced according to Splunk best practices.
*The application is now compatible with Splunk cluster environments.

New for Version 2.3:
* Fixed issues identified by AppInspect:
** Removed install_source_checksum from app.conf
** Fixed permissioning

New for Version 2.2:
* Fixed Fonts for Splunk versions <= 7.1

New for Version 2.1:
* Fixed URL bug (linking between dashboards)

New for version 2.0:
* Added support for Splunk CIM (implemented as part of the Technology Add-on)
* Moved all parsing to our Technology Add-on (which is now required install for the App to work)
* Updated App styling to match DatAlert Web UI
* Fixed display of double backslashes
 
New for version 1.15:
* Fixed inversed alert Severity values
 
New for version 1.13:
* Changed field extractions to use duser instead of samAcc (field extraction didn't work correctly with dusers containing spaces and commas)
 
New for version 1.12:
* Changed sourcetype to follow Splunks new guidelines (dls-cef-alerts -> varonis:dls:alerts)
* Added 'alt' app icons
 
New for version 1.11:
* Performance improvements
* Implementing the index macro per Splunk best practices