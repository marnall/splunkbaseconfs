# ClamAV app

This app looks at clamav and freshclam log files to report on usage, scan summary, and virus' discovered.

- ClamAV (https://www.clamav.net/). ClamAV® is an open source antivirus engine for detecting trojans, viruses, malware & other malicious threats.
- ClamAV is a registred trademark of Sourcefire, Inc. and Cisco Technology, Inc.

The author of this splunk app has no connection whatsoever with ClamAV, Sourcefire, and or Cisco. Other, than I think it's a f'ing cool product and no-one else has made a splunk app for its logs. :)


# Getting Started

This app has been created to work correctly with a stand-alone, distributed, and cloud installs of Splunk. Read the install notes carefully below with your splunk platform in mind.

You will need two apps:
1. ClamAV     https://splunkbase.splunk.com/app/1798/
  a. (this app)
2. TA-ClamAV  https://splunkbase.splunk.com/app/3619/


## New Install

This section is to install on a centralized or stand-alone splunk setup. 

1. Install ClamAV via Splunk UI.
2. Install TA-ClamAV via Splunk UI.
3. Read the index section, below, to enable your correct index settings.
4. Restart the Splunk server.


## Upgrading this app

1. Run the upgrade via the Splunk App management UI.
2. Or use the correct update methodology depending on your distributed design.


## Install for Distributed Splunk designs

For those who are running a distributed Splunk design or HA: ie separate forwarders, search heads, indexers, etc... Please follow these directions, depending on your design YMMV.  Please see this link for more instructions:  [http://docs.splunk.com/Documentation/AddOns/released/Overview/Installingadd-ons]

  
1. Install this App on your Search head(s).
2. See the README.txt notes to install the TA-ClamAV app on the remaining systems.


## Install for Splunk Cloud

I have not used Cloud yet. I believe you install this app via the UI.
Also install the TA-ClamAV app via the UI.


# Index Notes:

See the README.txt file in the TA-ClamAV app.
The TA app will control your index settings.


# What's in 1.0.5!

- Created TA-ClamAV to correctly support Distributed and Cloud splunk installs.
- NOTE: You will need to install the TA-ClamAV app to use this ClamAV version!
- Updated CIM.
- Validated app through Splunk App builder.
- Minor corrections and updates.
- Works with splunk 6.5 & 6.6.


# What's in 1.0.4!

- Updated some search string issues.
- Updated instructions for HA splunk install.
- Updated CIM items.


# What's in 1.0.3!

- Updated support for clamXav logs.
- Included Mac OSX set-up instructions.
- Added Common Information Model (CIM) 4.0 support.
- Updated file permissions.
- Updated default.meta file.
- Added Pivot Data Models.


# What's in 1.0.2!

- Fixed some extracts in props.conf file.


# What's in 1.0.1!

- Updated the logo.
- Updated the DLP dashboard.
- Verified works with Splunk 6.1.
- Changed app directory from "clamav" to "ClamAV".
  (This will install a second app. You will need to delete the old v1.0 app and copy over any "local/" files).


# What's in 1.0!

New app!

- Works with Splunk 6.0.
- TA for distributed Splunk designs.
- Search form.
- Dashboards on scan summary and agent logs.
- Dashboards on PUA, DLP and Quarantine results.


# Support

This is an open source project, no support provided. Please use splunk answers for help and assistance. Author monitors splunk answers and will provide help as best as possible.

