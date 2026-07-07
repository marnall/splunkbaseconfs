# Sysmon Tuning Helper

## Support
- Splunk 8.0, 7.1, 7.2, 7.3

## How This App Works
This app provides Dashboards and a lookup to go through your Sysmon logs and help tune out sources of large amounts of logs. 
* Start with the Events by EventCode dashboard and fill in the index and source for your Sysmon logs, and select a timeframe.
* Click on the EventCode to go to a drilled down dashboard of important fields from that EventCode. 
* From there click on the Value you want to exclude and it will add it to a tuning lookup.
* If you refresh the searches it will remove the tuned objects. 
* When you are done click on the "Review Tuning" button on the main dashboard and it will provide you a list of the Sysmon config changes you selected.
* On the review tuning dashboard, each line will have an "Investigate" and "Remove" link.
* Clicking "Investigate" will open a search with those events in a new tab to review.
* If you events don't show up you may need to set the time range.
* Clicking "Remove" will remove the line from the lookup. You will have to refresh to see the changes.

## About Sysmon Tuning Helper

Author - Dusty Miller
Version - 0.2.2

## Installation:
This app only needs to be installed on a search head you intend to use for tuning.
This app requires the TA-Microsoft-Sysmon.

# Support:
- This app is developer supported by Dusty Miller. 
- You can send any inquiries / comments / bugs to dusty.miller109@gmail.com.
- Response should be within a business day.

# Updates
0.2.2
- Fixed a default value and bug

0.2.1
- Fixed lookup and events by eventid view

0.2.0
- Updated lookup review to add ability to review tuning targets

0.1.0
- Initial Release
