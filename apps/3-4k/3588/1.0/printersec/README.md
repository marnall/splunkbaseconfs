## Splunk Application for HP Printer Security
This project is originally developed by students and staffs from Nanyang Polytechnic, School of IT in collaboration with HP under the partnership with Splunk Singapore.

The HP Printer Security application ingests HP printer's logs in real-time and monitor, detect and report critical security events through log analysis.

## Requirement
Log Format:
The app assumes the HP Printer(s) has been configured to output security event logs and forward to an syslog server. The syslog should be in this format: <timestamp> <source ip> <severity level>: <device>: <message>, e.g. 2016-12-06T17:54:25.324722+08:00 172.20.134.251 LPR.INFO: printer: peripheral low-power state.

App Dependency:
Currently the app makes use of the EventGen app at SplunkBase to randomly generate security events based on a sample syslog from an HP printer. This allows the app to showcase its features without the need of linking up to a real HP printer or syslog server. For this reason, the EventGen app needs to be installed at the same Splunk instance. User can change the settings at the inputs.conf file to read logs from a real syslog server.

## Version 1.0 Features
This release focuses on monitoring and reporting critical and high risk security events from HP printer(s). It comes with two dashboards: Security Posture and Event Investigator, as well as an alert that monitor such events in a weekly windows.

## Contributor
NYP: Ong Zhi Heng, Huang Wanling
Splunk Singapore: Philip Sow, Maverick Wong
HP: Junaid UR Rehman

## Feedback
huang_wanling [at] nyp.edu.sg
