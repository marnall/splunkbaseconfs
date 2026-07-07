App Version: 1.6.0
Author: Derdack GmbH
Contact: success@signl4.com

FEATURES:
Adds another alert action to your Splunk search alerts.
Allows you to send alert search results to your SIGNL4 team in order to notify people on duty via SMS text, voice, push, etc.

SETUP:
The app has one global property which is the team secret of your SIGNL4 team.
You can find it in the SIGNL4 app under settings -> APIs.
Enter that team secret as default team to notify.
If you do not override this secret in a specific search alert action with another SIGNL4 team secret, the globally configured team will be paged.
In the details of the search alert action you can also enter the name of a system or device category, the alert / Signl should be assigned to. This property can also remain blank in order to let SIGNL4 assign a category automatically.
