CryptoniteNXT App for Splunk (TM)
Copyright (C) 2016-2017 Cryptonite, LLC.  All rights reserved.


### Installation

This app should be installed on a search head. To install this app, first install:

* cefutils add-on (v1.2.4 or later)
* Splunk's CIM (v4.7 or later) https://splunkbase.splunk.com/app/1621/

Ensure that the splunk server has an IPv6 address, and that the various
CryptoniteNXT nodes can reach the splunk server on that address.

More information on installing or upgrading Splunk apps can be found here:
<http://docs.splunk.com/Documentation/Splunk/latest/Admin/Wheretogetmoreapps>


##### Known issues

If using a CIM version less than 4.9.x, the denials dashboard may not populate correctly. 
This is due to a dependency on new fields. All other dashboards should function properly.

