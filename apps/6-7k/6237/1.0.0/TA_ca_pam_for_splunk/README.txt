CA Privileged Access Manager (PAM) Add-on for Splunk
Copyright (C) 2021 CyberSecThreat Corporation Limited. All Rights Reserved.

================================================
Overview
================================================

This app provides field extraction, cim mapping(authentication) for CA Privileged Access Manager (PAM) in Splunk.

The field extraction accepts both Splunk native tcp/udp connections and rsyslog style syslog.

CA PAM supports both syslog and xsuite for Splunk, we do recommend use syslog which contains more information for investigation purpose.

================================================
Configuring Rsyslog
================================================

The timestamp of syslog format from CA PAM is not aligned. If you use rsyslog, you can reconfigure your rsyslog.conf as following:

For Redhat 8:
#module(load="builtin:omfile" Template="RSYSLOG_TraditionalFileFormat")
$template CustomFormat,"%timegenerated% %HOSTNAME% %syslogtag%%msg:::sp-if-no-1st-sp%%msg:::drop-last-lf%\n"
module(load="builtin:omfile" Template="CustomFormat")

For Redhat 7:
#$ActionFileDefaultTemplate RSYSLOG_TraditionalFileFormat
$template CustomFormat,"%timegenerated% %HOSTNAME% %syslogtag%%msg:::sp-if-no-1st-sp%%msg:::drop-last-lf%\n"
$ActionFileDefaultTemplate CustomFormat

================================================
Configuring Splunk
================================================
This app need to install on Splunk Search Head.

Install this app into Splunk by doing the following:

  1. Log in to Splunk Web and navigate to "Apps » Manage Apps" via the app dropdown at the top left of Splunk's user interface
  2. Click the "install app from file" button
  3. Upload the file by clicking "Choose file" and selecting the app
  4. Click upload
  5. Restart Splunk if a dialog asks you to

Configure the input sourcetype as ca:pam:syslog.

================================================
Useful macros
================================================

We do provided different useful macros which can correlate different logs. This is the most powerful part of this apps. You should explore those macros. Those name of macros are starting with CA_PAM*.

Also, we have provided some example inside macros.conf, you can extend the power by defining the correct lookup files and AD domain.

If there is any performance issues when using those macros, you can consider install this app on Heavy Forwarder/Indexer, create a new index, and enable TRANSFORMS-index_ca_pam inside props.conf and transforms.conf.

================================================
Known Limitations
================================================

N/A



================================================
Getting Support
================================================

This is an open source project and no active support is provided. If there is any issues, email to info@cybersecthreat.com during weekday business hours (GMT+8).




================================================
Change History
================================================

+---------+------------------------------------------------------------------------------------------------------------------+
| Version |  Changes                                                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 1.0.0   | Initial release                                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|