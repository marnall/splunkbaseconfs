Check Point Response Add-on for Splunk
======================================================================
This is an add-on powered by the Splunk Add-on Builder.

OVERVIEW
------------------------------
Check Point Response Add-on for Splunk is an integration module of Check Point for Splunk Enterprise Security Suite.

* Author - Check Point
* Version - 1.0.0
* Build - 1
* Creates Index - False
* Uses Source type - checkpoint:ar:response
* Prerequisites - This application is dependent on Splunk Enterprise Security Suite.
* Compatible with:
    - Splunk Enterprise version: 6.6.x, 7.0.x and 7.1.x
    - Splunk Enterprise Security version: 5.1.0 and 5.0.1
    - OS: Platform independent

OPEN SOURCE COMPONENTS AND LICENSES
-----------------------------------
* Some of the components included in Check Point Response Add-on for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects.
  pysmb 1.1.23 https://pysmb.readthedocs.io/en/latest/ (LICENSE https://pysmb.readthedocs.io/en/latest/#license)


APPLICATION SETUP
------------------------------
* On Splunk Search Head:
    * On Splunk Search head, install and configure the TA where Splunk Enterprise Security is configured to use Adaptive Response Action.

ALERT ACTION
------------------------------
* This app contains "Upload IOC to Check Point" alert action.

SAVED SEARCH
------------------------------
* This app contains a saved search named checkpoint_kvstore_update_search which periodically deletes the expired IOCs.

SUPPORT
------------------------------
* Support Offered: Yes
* Supported by Check Point team through Splunk Community on best effort

Copyright (C) by Check Point Software Technologies Ltd. All Rights Reserved.