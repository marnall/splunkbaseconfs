
# README for smIntegration
# 2018 by Aaron Chandler



#################################



# $L.Table.of.Contents

- To-Do
- About
- Support
- Installation
- Logical Name Solution
- Troubleshooting



#################################



# $L.ToDo:

- Build a GUI functionality to select whether the communication with SM should occur over HTTP or HTTPS,
  and develop the backend side to handle the latter
  - This release uses HTTP, on the assumption that your SM instance is on an internal LAN and the API
    servlet is therefore not requiring SSL, because SM would need to have a cert for every machine that
    wants to use the API over SSL.
- Build a functionality to allow administrators to re-label the fields in the alert action UI, based on
  how they are labeled in the Service Manager Incident screens
- Build a toggle to allow administrators to say "all Incidents take the same field values" or "per-alert
  field values"



#################################



# $L.About:

Author:                   Aaron Chandler (splSM on GitHub)

Version:                  1.0.2

What, Why, How, etc.:     This add-on allows a Splunk administrator to create saved searches and alerts, which
                          when triggered will create an Incident record in Service Manager, which is a robust
                          enterprise-grade ticketing solution often used for (among other things), IT Service
                          Management and cybersecurity Incident Resolution.

Compatible Products:      Intended for use with Splunk Enterprise, Cloud, or Light. To this point, I have
                          only worked with on-prem Splunk, but Cloud and Light should both run this add-on
                          as well. Intended to be used in concert with HP/HPE/MicroFocus Service Manager.

Supported Platforms:      This add-on is platform-independent.

Index-Time Operations:    None. No indexing occurs in this add-on. It involves outbound data from Splunk to SM.

Creates Indexes:          No.

Implements Summarization: Nope.

Assorted:                 This add-on involves no lookups, and this is not related to or involved with Splunk CIM.

Performance:              No benchmark tests have been performed on this add-on, as they are not particularly
                          needed for an add-on of this kind. However, for what it's worth: generating an event
                          which fires an alert, the alert being fired, the communication between Splunk and SM
                          occuring across the wire (not an internal LAN), a ticket being generated, and the JSON
                          response from SM being logged - all this has taken less than 2 seconds in my testing.

Scripts and/or Binaries:  createIncident.py is the primary worker bee of this add-on, which takes details
                          provided in the add-on setup and in the saved-search-specific alert, and then creates
                          Incident records in Service Manager.

v1.0.2 Release Notes:     - Ability to establish global SM connection, credentials, and API field captions.
    (& New Features)      - Ability to specify per-alert field values which can apply to only that alert.
                          - Scripted alert functionality which combines the above with details from the triggering
                            event to create an Incident ticket in SM.
                          - Suggested default API captions are provided, based on an out-of-box v9.52 instance
                            of Service Manager.
                          - Incident category when opening the ticket is hard-coded to "incident" in this release.



#################################



# $L.Support:

Support Boilerplate:      This add-on is offered as-is, with no guaranteed support mechanism. By downloading + installing,
                          you are indemnifying me (Aaron Chandler) of any responsibility for how it may impact your
                          system(s). Now that THAT is out of the way, if you have any installation hurdles or questions
                          or concerns or ideas (or catastrophes in your Prod environment), email me and I will do my
                          darndest to assist as soon as I can.

Contact Information:      splunk.consultant@outlook.com or sm.consultant@outlook.com

Hours of Email-Checking:  Monday to Friday, 0900 to 1700 EST

Estimated Response Time:  Before end of the current business day, or before the end of the next business day if
                          contact is made on a weekend

Bug/Enhancement Tracking: GitHub @ https://github.com/splSM/spl2smIntegration/issues



###########



# $L.Installation:

- This add-on should be installed on Search Head nodes.
- Drop this into bad boy into $SPLUNK_HOME/etc/apps or download from it from the GUI, etc.
- Use the Setup to establish global SM Connection and Credential Parameters, and set the
  Field Captions as exposed in SM's RESTful API.
  - You'll need to talk to your SM administrator to get a user/pass for the API.
    - The user must have the "RESTful API" capability word and rights to create Incident records.
  - Default captions are suggested, based on an out-of-box v9.52 Service Manager API.
  - The out-of-box v9.52 probsummary extaccess record still captions Subcategory and
    Area respectively as Area and Subarea, even though the Incident screen labels them
    as Subcategory and Area. For consistency, it is recommended that the Service Manager
    Administrator re-caption these in the probsummary extaccess record.
- That's it! The add-on is installed!
- Now, when you or your users are creating alerts which will generate SM Incident
  tickets, you can select which values will go into which fields.
  - These can be the same values for all alerts, or separate values - as you please, but in
    this release they will need to be re-entered for each alert if you choose the latter.

- Deploy to Distributed Search Head Cluster:
  You'll need to set the SM operator password on each node. Sorry about that, but since this
  add-on uses the storage/passwords API to encrypt the SM operator password, it is what it is.
  You can set every other global parameter in the Setup, and then only have to set the
  password on each node, though.



#################################



# $L.LogicalNameSolution:

Nowadays, Service Manager uses what was called (when the feature first was released) the Logical
Name Solution. In a nutshell, this allows for multiple Configuration Items (CIs; device table
records) with the same *name* to exist, while still giving every CI a unique ID. This could impact
what you send in for the Affected Service and Affected CI fields, because an Out-of-Box SM is
going to want those in logical.name format (for example: CI123456) and not in a display.name format
(for example: hostname.domain.com). Rather than you having to ask every time you want to use a
different CI in your integration, it would behoove the SM administrators to add something like these
lines to the expressions on the probsummary extaccess record:

if (affected.item in $L.file)~#"CI" then (affected.item in $L.file=jscall("SplunkIntegration.getLogicalNameByDisplayName", affected.item in $L.file));if (logical.name in $L.file)~#"CI" then (logical.name in $L.file=jscall("SplunkIntegration.getLogicalNameByDisplayName", logical.name in $L.file)) 

The SM administrators could then create a ScriptLibrary named SplunkIntegration with this function:

function getLogicalNameByDisplayName(displayName) {
   if ( displayName == null ) { return 'Display Name not provided!'; }
   var device = new SCFile('device');
   if ( device.doSelect('display.name="' + displayName + '"') == RC_SUCCESS ) { return device.logical_name; }
   else { return 'Logical Name not found by Display Name provided!'; }
}

Also, there is already a DisplayName ScriptLibrary which the SM administrators could use instead.



#################################



# $L.Troubleshooting:

*** I will add to this section as I indentify common issues you may face in the Service Manager
    REST API and/or things you may encounter when getting the Splunk side of this add-on working.
