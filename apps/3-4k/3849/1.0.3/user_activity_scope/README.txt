User Activity Scope
version 1.0.2

This will not have full functionality in Splunk Free.

Users need dispatch_rest_to_indexers capability in order to access the data from this app.

Each panel is pre-built and can be added into other apps and dashboards. 

Top Dashboards:
Both panels are for the Last 30 Days.
Clicking on any row will open the dashboard displayed in that row in a new tab.

5 most recent dashboards:
This panel will display the 5 most recent apps viewed by the current user. 
The table should diplay the app name, the title and description of the app, the last time it was viewed by current user, 
and how many times it's been viewed.

Top 20 dashboards Used:
This will display similar information as the above panel, however it is the most viewed dashboards for the current user.

Definitions:
appName: Name of the app the dashboard belongs to
title: Title of the dashboard
description: If filled out, description of the dashboard
lastViewed: The last time the dashboard was viewed by the user
timesViewed: The number of times the dashboard was viewed by the user in the Last 30 Days


Search History:

This displays search history for the Last 30 Days.
Information included in the table is the time of when the search was executed, sid, search string, 
and the time range of the search.
Clicking on any row will open up the search in a new tab with the original start and end time.
NOTE: There may be errors if All Time was the time frame. I apologize, I'm working on fixes for those.

Definitions:
timestamp: This is the date and time the search was executed
sid: This is the search id associated with the search
fullSearch: This is the full search string
apiStartTime: This is the earliest time the search queries
apiEndTime: This is the lastest time the search queries


References:

This is a nice cheet sheet that links to multiple Splunk references for help, such as Splunk Docs and Splunk Answers.
If the image doesn't render scaled to the page, refresh to try again.
