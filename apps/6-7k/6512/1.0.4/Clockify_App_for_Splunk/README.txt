Clockify App for Splunk
Author: Avotrix Inc
Version:1.0.0

Description
Clockify App for Splunk lets you keep track team of activities on basis of projects, time, productivity and tasks on Clokify. One can get multiple workspaces entries within the single dashboard here,so you dont worry about switching from one workspace to another to see clockify app statistics

Now you can track your billable as well as Nonbillable Projects in order to get insights and drive your team and projects in an optimize way.

Also get information about the client billing details on tips with this app

Prerequisites

Before installing this app ensure Clockify Add-on for Splunk is installed

Installation
This app should be installed only on a Splunk Search Head. You will need to restart Splunk after installing the app

Configuration
To get the dashboard populated please update the macro "index-name" with the index you have created to get the data in Splunk. 

Scheduled Searches
The following reports and lookups have been scheduled and can be altered as per required

Reports
Clockify-Monthly report on user: This report gives the time entries filled by the user within the workspace of the respective month. Update the workspace in the query as per your requirment
Clockify-Weekly report on user: This report gives the time entries filled by the user within the workspace of the respective week. Update the workspace in the query as per your requirment
Lookups
The lookups are scheduled to run every sixth hour everyday, can be altered. Must enable these for dashboard population.

Clockify-Username Lookup: Collects username from the respective workspace.
Clockify-Tasks Lookup: Collects tasks name from the respective workspace.
Clockify-Project Lookup: Collects Project name from the respective workspace.
Clockify-Workspace Lookup: Collects Workspace name
Notifications
Clockify-Time entries not filled within a week: This alert will get trigger only if any users time entries are not filled during last week. It is scheduled to run every monday and collects data from last week

Contact us:
Please feel free to reach out to us in case of any queries at support@avotrix.com.
# Binary File Declaration
# Binary File Declaration
# Binary File Declaration
