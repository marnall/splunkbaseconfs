Data Add-on for Firebind
Copyright (C) 2014 Firebind Inc. All rights reserved.

Splunk, Splunk Apps and Splunk Enterprise are registered trademarks of 
Splunk Inc. 

Version Support
---------------
Version 1.1 of the Data Add-on for Firebind supports Splunk Enterprise 
6.1 or better. Other of Splunk Enterprise versions may work but are not
recommended or supported.

System Requirements
-------------------
This Add-on will work on all systems supported by Splunk Enterprise.

Installation
------------
Obtain the installation file from Splunk Apps (firebind-addon.spl) and use
the "App Manager->Install app from file" menu item to upload the file to
your installation.

Configuration
-------------
The data models provided by this add-on require a sourcetype of 'firebind'.
When configuring your Input (TCP, Fowarder, etc) please create and associate
the incoming Firebind data with the source type 'firebind'.

Troubleshooting
---------------
It is recommended that you use Pivot to verify a non-zero number of events
associated with the data model.

Support
-------
Support is available by email. Send a detailed description of your issue and
contact information to support@firebind.com

Running the Add-on
------------------
This add-on can be used for reporting, dashboards and charting.

Miscellaneous
-------------
Splunk and Splunk Enterprise are registered trademarks of Splunk Inc. Use of 
these trademarks is in accordance with the Naming Guidelines as documented
here: 
http://docs.splunk.com/Documentation/Splunkbase/latest/Splunkbase/Namingguidelines
 