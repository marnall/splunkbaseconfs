# CloudGenix Flow Add-on for Splunk

## Support
- Splunk 7.3, 8.0, 8.1, 8.2

## How This App Works
This app provides CIM-compatible knowledge objects for working with CloudGenix flow logs.

## About Hurricane Labs Add-on for Windows PowerShell Transcript

| Author | Tom Kopchak, Hurricane Labs |
| --- | --- |
| App Version | 1.0.0 |
| Vendor Products | CloudGenix - Flow Logs |
| Has index-time operations | false |
| Create an index | false |
| Implements summarization | false |

## Installation:
This add-on should be installed on search heads

Configured your CloudGenix flow logs to be collected and indexed into Splunk with the sourcetype of cloudgenix:flow.  We recommend using a syslog-ng server with a filter to capture these logs.  

## References:
Vendor documentation of log format use for this app is available here: https://docs.paloaltonetworks.com/prisma/prisma-sd-wan/prisma-sd-wan-admin/prisma-sd-wan-sites-and-devices/use-external-services-for-monitoring/syslog-server-support-in-prisma-sd-wan/syslog-flow-export 

# Support:
- This app is developer supported by Hurricane Labs. 
- You can send any inquiries / comments / bugs to splunk-app@hurricanelabs.com
- Response should be relatively fast if emails are sent between 9am-5pm (Eastern)


# Updates
1.0.0
-Initial release
