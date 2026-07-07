## Table of Contents

### OVERVIEW

* About the TA for Digital Guardian
* Release notes
* Support and resources

### INSTALLATION AND CONFIGURATION

* Hardware and software requirements
* Installation steps
* Deploy to single server instance
* Deploy to distributed deployment
* Deploy to distributed deployment with Search Head Pooling
* Deploy to distributed deployment with Search Head Clustering
* Deploy to Splunk Cloud
* Configure TA for Digital Guardian

### USER GUIDE

* Data types
* Lookups

---

### OVERVIEW

#### About the TA for Digital Guardian

* Author: Digital Guardian
* App Version: 2.0.4
* Vendor Products: Digital Guardian 7.0.0 and above
* Has index-time operations: true, this add-on must be placed on indexers
* Create an index: true, impacts disk storage
* Implements summarization: false

The Digital Guardian App for Splunk Enterprise lets customers understand risks to sensitive data across the enterprise from insider and outsider threats and respond appropriately. Users can improve incident response and investigation times by leveraging Splunk’s enterprise search capabilities across Digital Guardian event and alert data. The App works with this Add-on which brings Digital Guardian events and alerts into Splunk Enterprise. This Add-on is designed for Digital Guardian 7.0.0 and above. For use with previous versions please contact Digital Guardian.

##### Scripts and binaries

None

#### Release notes

2.0.4 - 3/12/2018

* Updated file permissions

##### About this release

Version 1.3.0 of the TA for Digital Guardian is compatible with:

* Splunk Enterprise versions: 6.2, 6.1
* CIM: 4.1, 4.0, 3.0
* Platforms: Platform independent
* Vendor Products: Digital Guardian 7.0.0 and above
* Lookup file changes: Added severity_lookup

##### New features

Version 1.3.0 TA for Digital Guardian includes the following new features:

* Moved Lookup Tables from App to TA (computer_type_lookup, dg_protocol_lookup, drive_type_lookup, email_recepient_type_lookup, file_encryption_lookup, network_direction_lookup, operations_lookup, rule_action_type_lookup, scanvalue_lookup)
* Added Custom Event functionality for Alerts
* Update Version Number to match digitalguardian_web

##### Fixed issues

Version 1.1.2 of the TA for Digital Guardian fixes the following issues:

* Fixed Bug in props.conf

Version 1.1.1 of the TA for Digital Guardian fixes the following issues:

* Updated EventGen Samples
* Updated Documentation
* Removed hidden files

Version 1.1 of the TA for Digital Guardian fixes the following issues:

* Fixed CIM Compliance

##### Support and resources

**Questions and Answers**
Access questions and answers about the TA for Digital Guardian at http://answers.splunk.com/answers/app/1878

**Support**

* Support URL: https://digitalguardian.force.com/support/login
* How to get support: via above support portal URL. Login is required for Digital Guardian customers; customers who do not have a support login may apply for one at support@digitalguardian.com
* Support hours: 24/7
* Observed holidays: Closed on major US holidays.
* Response: all cases submitted will be confirmed via email; response time based on severity
* Cases are tracked in the salesforce.com system

## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

TA for Digital Guardian supports the following server platforms in the versions supported by Splunk Enterprise:

* Linux
* Windows
* Solaris

#### Software requirements

To function properly, TA for Digital Guardian requires the following software:

* Digital Guardian 7.0.0 and above

#### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Download

Download the TA for Digital Guardian at https://apps.splunk.com/app/1878/.

#### Installation steps

To install and configure this app on your supported platform, follow these steps:

1.  Download and Deploy the add-on to either a single Splunk Enterprise server or a distributed deployment.
1.  Configure your Digital Guardian server to export data to your single instance or your forwarder.
1.  Configure your inputs to get your Digital Guardian data into Splunk Enterprise.

##### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1.  Download from Splunk Apps.
1.  In Splunk Web, click Apps > Manage Apps.
1.  Click Install app from file.
1.  Locate the downloaded file and click Upload.
1.  Verify that the add-on appears in the list of apps and add-ons. You can also find it on the server at $SPLUNK_HOME/etc/apps/TA-digitalguardian.
1.  Copy $SPLUNK_HOME/etc/apps/TA-digitalguardian/default/inputs.conf.example to $SPLUNK_HOME/etc/apps/TA-digitalguardian/local/inputs.conf
1.  Edit local/inputs.conf to match your log locations.
1.  Restart Splunk

##### Deploy to distributed deployment

**Install to search head**

1.  Download from Splunk Apps.
1.  In Splunk Web, click Apps > Manage Apps.
1.  Click Install app from file.
1.  Locate the downloaded file and click Upload.
1.  Verify that the add-on appears in the list of apps and add-ons. You can also find it on the server at $SPLUNK_HOME/etc/apps/TA-digitalguardian.

**Install to indexers**

1.  Download from Splunk Apps.
1.  In Splunk Web, click Apps > Manage Apps.
1.  Click Install app from file.
1.  Locate the downloaded file and click Upload.
1.  Verify that the add-on appears in the list of apps and add-ons. You can also find it on the server at $SPLUNK_HOME/etc/apps/TA-digitalguardian.
1.  Create an index called digitalguardian to match the new local/inputs.conf.

**Install to forwarders**

1.  Upload the TA-digitalguardian folder to the forwarder and put into the $SPLUNK_HOME/etc/apps directory.
1.  Copy $SPLUNK_HOME/etc/apps/TA-digitalguardian/default/inputs.conf to $SPLUNK_HOME/etc/apps/TA-digitalguardian/local
1.  Edit local/inputs.conf to match your log locations.
1.  Restart Splunk

#### Configure TA for Digital Guardian

Configuration Steps are in Installation Instructions.

## USER GUIDE

Digital Guardian offers security’s most technologically advanced endpoint agent. Only Digital Guardian ends data theft by protecting sensitive data from skilled insiders and persistent outside attackers.

The Digital Guardian App for Splunk Enterprise lets customers understand risks to sensitive data across the enterprise from insider and outsider threats and respond appropriately. Users can improve incident response and investigation times by leveraging Splunk’s enterprise search capabilities across Digital Guardian event and alert data. The App includes an Add-on which brings Digital Guardian events and alerts into Splunk Enterprise. The Add-on is designed for Digital Guardian 7.0.0 and above. For use with previous versions please contact Digital Guardian.

The Digital Guardian App for Splunk Enterprise includes seven dashboards that visualize Digital Guardian events and alerts with advanced abilities to drill down and filter data to pinpoint threats, investigate and respond. Dashboards include:

* Data Classification: Show that sensitive data is effectively identified and classified
* Alerts: Monitor policy violations, validate appropriate controls are in place and provide input into incident response process
* Events: Monitor data leaving the enterprise by channel - Email, Print, Removable Devices and Network Uploads. Understand channel usage to establish risk level.
* Process: Monitor process (application) access to data and identify anomalies
* Data Egress: Monitor data movement to understand how and where data is put at risk to improve classification and controls
* Advanced Threat Detection: Monitor malware alerts resulting from behavioral detection rules in Digital Guardian’s advanced threat module
* Operations: Monitor operations of the Digital Guardian IT infrastructure

These data types support the following Common Information Model data models:

* Alerts

### Lookups

The TA for Digital Guardian contains 1 lookup file.

** severity_lookup **

Translates Severity Code to Human Readable Name.

* File location: TA-digitalguardian/lookups/severity_lookup.csv
* Lookup fields: key,value
* Lookup contents:

```
key,value
1,Informational
2,Low
3,Medium
4,High
5,Critical
```

** computer_type_lookup **

Translates Computer Type Code to Human Readable Name.

* File location: TA-digitalguardian/lookups/computer_type_lookup.csv
* Lookup fields: key,value
* Lookup contents:

```
key,value
0,Windows
1,Linux
2,Solaris
3,Mac
4,iOSMobile
255,Unknown
```

** dg_protocol_lookup **

Translates Code to Human Readable Name.

* File location: TA-digitalguardian/lookups/dg_protocol_lookup.csv
* Lookup fields: key,value
* Lookup contents:

```
key,value
0,Unknown
1,TCP
2,UDP
3,IPSec
4,IPX
5,IrDA
6,Bluetooth
7,HTTP
```

** drive_type_lookup **

Translates Code to Human Readable Name.

* File location: TA-digitalguardian/lookups/drive_type_lookup.csv
* Lookup fields: key,value
* Lookup contents:

```
key,value
0,Unknown
1,No Root Dir
2,Removable
3,Fixed
4,Remote
5,CD/DVD
6,Ramdisk
7,None
8,Screen
9,URL
255,All Removable Media
```

** email_recipient_type_lookup **

Translates Code to Human Readable Name.

* File location: TA-digitalguardian/lookups/email_recipient_type_lookup.csv
* Lookup fields: key,value
* Lookup contents:

```
key,value
0,To
1,Cc
2,Bcc
```

** file_encryption_lookup **

Translates Computer Type Code to Human Readable Name.

* File location: TA-digitalguardian/lookups/file_encryption_lookup.csv
* Lookup fields: key,value
* Lookup contents:

```
key,value
0,Not Encrypted
1,AES256-adaptive
2,3DES-adaptive
3,Std. ZIP auto-generate PW
4,Std. ZIP-prompt for password
5,AES256 ZIP auto-generate PW
6,AES256 ZIP-prompt for password
7,AES256-password protected
8,3DES-password protected
9,AES256-password protected (SID)
10,3DES-password protected (SID)
11,S/MIME
```

** network_direction_lookup **

Translates Code to Human Readable Name.

* File location: TA-digitalguardian/lookups/network_direction_lookup.csv
* Lookup fields: key,value
* Lookup contents:

```
key,value
False,Inbound
True,Outbound
```

** operations_lookup **

Translates Code to Human Readable Name.

* File location: TA-digitalguardian/lookups/operations_lookup.csv
* Lookup fields: key,value
* Lookup contents:

```
key,Operation
0,Unknown
1,CD/DVD Burn
2,Network Transfer Download
3,Network Transfer Upload
4,Network Operation
5,File Archive
6,File Extract
7,File Save As
8,File Edit
9,File Create
10,File Delete
11,File Copy
12,File Move
13,File Open
14,File Rename
15,File Read
16,File Write
17,File Recycle
18,File Restore
19,File Set Information
20,File Close
21,Application Data Exchange
22,Print
23,User Logon
24,User Logoff
27,Application Start
28,Send Mail
29,ADE Print Screen
30,ADE Print Process
31,ADE Cut
34,File Decrypt
35,ADE Screen Capture
36,Attach Mail
38,ADE Insert File
39,ADE Insert New Object
40,Document Repository
41,File View
42,Device Detected
43,Device Missing
44,Device Added
45,Device Removed
46,Application Action
47,Active Sync Send
48,Active Sync Receive
49,DLL Load
50,Custom Event
51,Timer Event
52,Registry Event
53,Hook Event
54,Device Open
64,Network Device
```

** rule_action_type_lookup **

Translates Computer Type Code to Human Readable Name.

* File location: TA-digitalguardian/lookups/rule_action_type_lookup.csv
* Lookup fields: key,value
* Lookup contents:

```
key,value
1,Continue
2,Prompt
3,Block
4,Lockdown
7,Classify
8,Encrypt
10,Vault
```

** scanvalue_lookup **

Translates Computer Type Code to Human Readable Name.

* File location: TA-digitalguardian/lookups/scanvalue_lookup.csv
* Lookup fields: key,value
* Lookup contents:

```
key,value
0,Scanned
1,Suspicious
2,Unknown
3,Not Submitted
```
