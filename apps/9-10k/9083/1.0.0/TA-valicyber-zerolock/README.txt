Vali Cyber ZeroLock Add-on for Splunk (TA-valicyber-zerolock)
============================================================

Version:  1.0.0
Vendor:   Vali Cyber
Product:  ZeroLock
Author:   Vali Cyber

Overview
--------
This Technology Add-on (TA) provides search-time parsing and Splunk Common
Information Model (CIM) normalization for ZeroLock Management Console (ZMC)
activity and alert data. ZeroLock is runtime security for the ESXi and Linux
hypervisor layer; this add-on lets its telemetry populate the Authentication,
Malware, Intrusion Detection, and Change data models in Splunk Enterprise
Security.

Data collection
---------------
ZeroLock forwards records to Splunk HTTP Event Collector (HEC) using its
built-in Splunk activity forwarder. This add-on does NOT collect data itself;
it only parses and normalizes data already arriving on HEC with sourcetype
"valicyber:zerolock". See the top-level README.md for HEC setup steps.

Sourcetype
----------
  valicyber:zerolock

CIM data models populated
-------------------------
  Authentication        login / logout / failed login
  Malware               ransomware / cryptojacking
  Intrusion Detection   tampering / blocked / program, file, network access, ssh-mfa
  Change                policy / role / credential / MFA changes

Dependencies
------------
  Splunk Common Information Model (CIM) Add-on (for data-model acceleration).

Support
-------
  support@valicyber.com
