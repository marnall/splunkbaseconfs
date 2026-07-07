# PingAccess App for Splunk

Developed by Ping Identity, the PingAccess App for Splunk gathers and presents transaction metrics from PingAccess
through a series of customized reports and graphical illustrations. 

The application enables identity and access
management (IAM) administrators, architects, and security managers to easily obtain custom reporting for all PingAccess
log data, view authorization events per app, engine, agent, and type, and analyze that event data over time. 

The customized reports display number of users seen, number of sessions, rule failures, most popular resources,
geo-mapping  of IP addresses, and other key events.

## Installation

Please refer to the PingAccess logging configuration guide:
https://docs.pingidentity.com/pingaccess/latest/configuring_and_customizing_pingaccess/pa_writing_audit_logs_for_splunk.html


## Compatibility

This app is designed for PingAccess 6.2 and later. 

In versions prior to 6.2, PingAccess lacks the fields required to distinguish where responses came from, and thus cannot
separate data into the Application/Agent/Third-Party Service/Token Provider pages. The Application page will display
using the captured data, however the metrics displayed will be inaccurate.

------------------------
Copyright 2026\
Ping Identity Corporation\
1001 17th Street, Suite 100\
Denver, CO 80202\
U.S.A.

