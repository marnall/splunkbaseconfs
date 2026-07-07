##Readme for the Tripwire IP360 App for Splunk Enterprise

##Author: Fortra's Tripwire
##Version: 4.0.1


#PREREQUISITES:
* Tripwire IP360 Add-on for Splunk Enterprise (version 4.0.1)
* Splunk 8.x or above
* IP360 VnE 9.1.5 or above


#CHANGES AND NEW FEATURES:
VERSION 4.0.1
   1. Revised to meet the specifications for Splunkbase hosting for Splunk Enterprise.
   2. The warnings from the Upgrade Readiness App have been resolved to ensure compatibility with recent releases of Splunk.
   3. The validation warnings in the app's dashboards in the app have been resolved.

VERSION 2.1.2
   1. Fixed an issue with applications.

VERSION 2.1.1
   1. Added support for IP360 versions 8.0.0 and above.
   2. Fixed an issue with OS groups.
   3. Fixed an issue with ip360_scan_status input rising column.

VERSION 2.1.0
   1. Fixed an issue with pulling in network groups
   2. Renamed the Add-on to comply with Splunk Enterprise Security naming conventions
   
VERSION 2.0.0
   1. Added a stand-alone TA for Tripwire IP360

#INSTALLATION:
The Tripwire IP360 App for Splunk Enterprise uses the data provided by the Tripwire IP360 Technology Add-on (TA) for Splunk.  The TA must
be downloaded, installed and properly configured prior to using this App.

Steps:
1. Install the Tripwire IP360 Add-on for Splunk Enterprise version 4.0.1 (available from Splunkbase) and follow the installation instructions.
2. Unzip the tripwire-ip360-app-for-splunk-enterprise_401.zip file.  This file contains the .spl file you will install.
3. Install the Tripwire IP360 App for Splunk Enterprise 
    	a. In Splunk Enterprise, Navigate to "Manage Apps" then "Install app from file"
	b. Select the ".spl" file containing the Tripwire IP360 Add-on for Splunk Enterprise and click upload
	c. Restart Splunk Enterprise as prompted

#DOCUMENTATION:
       - Link to project's website: https://www.tripwire.com/products/integrations/splunk
       - For support, contact support@tripwire.com
