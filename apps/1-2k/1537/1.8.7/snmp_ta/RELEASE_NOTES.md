# SNMP Modular Input

1.8.7
-----
* just a version bump for Splunkbase requirements 

1.8.6
-----
* upgraded the internal Splunk Python SDK to v2.0.2. 
* this release will require Python version 3 to run

1.8.5
-----
* added a custom config file,  snmpv3_usm_users.conf , which will allow you to setup multiple SNMPv3 USM Users for receiving Traps on the same port.

1.8.4
-----
* in some rare circumstances , and only on Windows , there may be permission errors rolling log files when you have configured multiple stanzas.Added a patch to uniquely name log files on a per stanza basis.

1.8.3
-----
* added some code that calls `tasklist` on Windows to detect and kill rogue snmp.py processes
* a few minor code tidyups

1.8.2
-----
* some minor regex field extraction tweaks to the snmp_attributes and snmp_traps sourcetypes

1.8.1
-----
* fixed some incorrect extractions for sourcetypes
* added more authentication protocols for SNMPv3

1.8.0
-----
* general robustification around MIB loading/compiling and better error messages to help diagnose issues with your custom vendor MIBs

1.7.9
-----
* upgraded the Splunk Python SDK to v 1.6.18 to meet the latest App Inspect/Cloud Vetting rules.

1.7.8
-----
* added low level pysnmp library debug logging to the logging output if level "DEBUG" is chosen

1.7.7
-----
* can now configure an engine id for a USM User for receiving v3 traps

1.7.6
-----
* Patch pysnmp for COUNTER/TIMETICKS encodings that might decode into a negative value

1.7.5
-----
* ensure DefaultResponseHandler doesn't emit empty content
* ensure that retrieved credentials always contain some placeholder String value in case no password values are returned from Splunk's REST API

1.7.4
-----
* added flag to optionally disable process state checking

1.7.3
-----
* fix to Process state checking for Windows environment

1.7.2
-----
* do not index end of MIB view messages for SNMP walking operations in the Default Response Handler.

1.7.1
-----
* minor patch to tighten up lifecycle checking of the SNMP process

1.7
-----
* updated the core version of `pysnmp` to the latest v4.4.12
* updated the core version of `pyasn1` to the latest v0.4.8
* general code refactoring to support the new libraries and maintain backwards compatibility
* added the `pysmi` library v0.3.4 to support compiling MIBs to Python modules at runtime
* for SNMP v3 , the `pycrypto` package is no longer required , instead you should now use the `pycryptodomex` package. More details in the README docs on installing the `pycryptodomex` package.
* plain text MIBS can now be added to the configuration and will be automatically compiled into Python modules for you , no more need to pre compile (although you can still pre compile if you wish using the built in midbump.py script)
* can now toggle `lexicographic mode` on/off for SNMP walking operations using GETNEXT and GETBULK. This setting governs if the entire MIB should be walked to the end or just the OIDs within the scope of the OIDs you start walking from.
* better informational logging
* added 2 new default sourcetypes with better timestamp extraction , `snmp_traps` and `snmp_attributes`
* added the option to use a System python rather than Splunk's built-in python , which you'll need for installing/running SNMP v3 dependencys
* adding in self monitoring logic to kill any `snmp.py` processes that splunkd doesn't kill when you disable an input.
* removed the dependency on the `splunk` package from site-packages. Now using the Splunk Python SDK for all API operations.

1.6.9
-----
* upgraded logging functionality

1.6.8
-----
* docs update

1.6.7
-----
* added a setup page to encrypt any credentials you require in your configuration

1.6.6
-----
* enforced python3 for execution of the modular input script.If you require Python2.7 , then download a prior version (such as 1.6.5).

1.6.5
-----
* general appinspect tidy ups

1.6.4
-----
* general appinspect tidy ups

1.6.3
-----
* minor bug fix

1.6.2
-----
* minor documentation update to better describe setting the trap host
* adjusted Attribute polling logic to reinitialize after an error

1.6.1
-----
*  minor tweaks to threading code logic for polling SNMP OID attributes

1.6
-----
* Python 2.7 and 3+ compatibility

1.5
-----
* fixed Splunk 8 compatibility for manager.xml file

1.4.2
-----
* updated docs

1.4.1
-----
* added trial key functionality

1.4
-----
* docs updated

1.3
-----
* Added an activation key requirement , visit http://www.baboonbones.com/#activation to obtain a non-expiring key
* Docs updated
* Splunk 7.1 compatible

1.2.7
-----

* Merged in community Pull requests  
Add a new option to get subtree  
Add a new option to perform rDNS for trap source  
Fix to resolve missing server extractions on the SNMPv3 trap receiver  


1.2.6
-----

* In the destination field for polling attributes , you can now optionally specify a comma delimited list of hosts

1.2.5
-----

* Fixed Bug in UI that prevented declaring custom MIB Names when in listen traps mode

1.2.4
-----
* Fixed host field extraction for receiving v2 traps

1.2.3
-----
* Minor code fixes

1.2.2
-----
* Updated the manager UI

1.2.1
-----
* Minor cosmetic fixes

1.2
---
* SNMP v3 support , please follow the docs regarding pycrypto dependencies

* pysnmp library update to 4.2.5

* Support for plugging in custom response handlers that can format the raw SNMP data in a particular format or perform preprocessing on the raw SNMP data before indexing in Splunk. Has a default response handler which produces the same output as previous versions.Also ships with an example JSONFormatterResponseHandler.

* Robustified exception handling

* More detailed logging