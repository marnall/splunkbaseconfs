# Resilient Add-On for Splunk and Splunk ES
v1.1.0

## Description

The Resilient Add-On provides the capability of escalating a Splunk alert or Splunk ES notable event to a Resilient incident.

## Release Notes
<!--
  Specify all changes in this release. Do not remove the release 
  notes of a previous release
-->
- Added support for Python 3

## System Requirements

- Splunk version 8.0 or later for Python 3 support
- Splunk ES 6.1.0 or later for Python 3 support
- Splunk CIM Framework. **Note: The Add-On depends on Splunk CIM. Please install CIM before installing the Add-On.**
- Resilient platform version 35 or later
- Ability to connect directly from Splunk to your Resilient server with HTTPS on port 443
- A dedicated Resilient Administrator or equivalent account on the Resilient platform. This can be any account that has the permission to create incidents and simulations, and view and modify administrator and customization settings. You need to know the account username and password. 

    NOTE: Should you later change the dedicated Resilient account to another user, the new user must also have the permission to edit incidents, in addition to the permission to create incidents and view and modify administrator and customization settings. The edit permission is necessary so that the integration can continue to modify or synchronize the incidents escalated by the original user account.
    
    You can refer to the [Playbook Designer Guide](https://www.ibm.com/support/knowledgecenter/SSBRUQ_37.0.0/doc/playbook/resilient_playbook_toolkit_simulations.html) for more information about simulations.

- Splunk admin role for the user that will install and set up Resilient Add-On and for all other users that need to add the Add-On as an Alert Action or an Adaptive Response action for a correlation search.

## Installation and Setup

For Splunk Cloud and Splunk ES Cloud users, contact Splunk Support to create a ticket for installing the Resilient Add-On.

If you have installed Splunk or Splunk on-premises, you can download and install the add-on from Splunkbase. Alternatively, you can request an installer from IBM Resilient.
After installing the add-on and restarting Splunk, navigate back to the App Manager screen. Click Set up in the Resilient row. Fill out the required attributes for your Resilient platform and click Save. When you save, the Set Up program performs the following:

- Retrieves the incident definition from the Resilient platform, so that all fields, including custom fields, are catalogued.
NOTE: If a Resilient administrator adds custom fields after you run Set Up, you need to run Set Up again to capture the fields. 
- Tests the configuration to verify that the connection is successful. If the configuration saves successfully, you are up and running.

![Configuration](images/setup.png)

## Support

For additional support, go to [IBM Support](https://ibm.com/mysupport). 

Including relevant information will help us resolve your issue:
- version of Splunk server
- version of Enterprise Security Add-On
- version of Resilient Add-On
- if using Splunk 8 - which Python interpreter your server is using
- steps/screenshots that will help us reproduce your issue

Including log files located in $SPLUNK_HOME/var/log/splunk:
- splunkd.log
- python.log 
- resilient_config_handler.log
- resilient_modalert.log
