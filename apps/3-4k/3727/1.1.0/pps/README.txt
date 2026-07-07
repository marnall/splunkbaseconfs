Copyright (c) 2023 by Proofpoint, Inc.  All Rights Reserved.

Proofpoint, Proofpoint Protection Server and the Proofpoint logos are trademarks or registered trademarks of Proofpoint, Inc.

Product Name: Proofpoint Email Security App for Splunk
Author: Proofpoint Inc
Version: 1.1.0
Date: 2023-11-10
Splunk requirements: Splunk Enterprise v9.1.x or v9.0.x

Introduction:

This main app will help users to provide visualization dashboards and reports for data collected using add-on. 


PREREQUISITES:

1. Splunk Enterprise v9.1.x or v9.0.x (tested on Windows and Linux Operating Systems).
2. Proofpoint Email Security App for Splunk - file or download from the Splunk App Store.
3. Add-on for PPS log or add-on for TAP.


Installation:

The PPS app can be installed from the Splunkbase App Store or using an installation package from a local system. Both methods are described below.

1. Installing the PPS app from Splunkbase
a. In the Splunk Web Home page, on top left corner, click on the "Manage Apps" gear icon.
b. In the Apps page, click on the "Browse more apps" button.
c. In the Browse More Apps page, search for "Proofpoint Email Security App for Splunk", which should appear at the top of the search result. Click on Install button.
d. Upon successful installation, the add-on will be in the listing in the Apps page.

2. Installing the PPS app from an installation file:
a. In the Splunk Web Home page, on the top left corner, click on the "Manage Apps" gear icon. 
b. In the Apps page, click on the "Install app from file" button.
c. To install, select the add-on package file (for example, pps_51.tar.gz).
d. Upon successful installation, the add-on will be in the listing in the Apps page.


Configuration:

Add-ons should be installed and configured before using main App.

Data models for PPS logs must be accelerated to improve performance. To accelerate Data models for Filter or MTA logs:
1. Go to "Settings" -> "Data Models"
2. Select "Proofpoint Email Security App for Splunk" app in the filter.
3. Click on "Edit" action for the data model you want to accelerate.
4. Click on "Edit Acceleration".
5. Check the "Accelerate" checkbox and select "Summary Range" ("7 Days" is recommended).
6. Click on "Save".
