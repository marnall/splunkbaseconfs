# README #
The KOM App reports on Splunk knowledge object usage, performance and edits through a number of dashboards.

Description:
This app provides a knowledge object (KO) usage overview.  The app highights KO usage, what is being used and what is no longer used.  Splunk admins can review what KO are used, how often and the resourse consumption over time.  The app currently focus on Dashboards and Reports/Alerts but also shows details for lookups and macros.

In addition, the app allows admin to review KO change actions for audit purposes.
Note:  The app will by default write KO metrics and UI access event details from _internal to the summary index.  If you already make the summary index available to non-admin users then please change the macro to use your own target summary index.  One is defined in "default/indexes.summary".  Rename the config file to indexes.conf.

Key features:
* Overview of Dashboard, Reports, Lookups and Macro usage.  Highlighting both active and inactive assets.
* Reporting of all change actions to KOs by users, based on the audit index.
* Reporting of Dashboard executions and resource consumption to identify resource hungry dashboard and analyse cause.
* Reporting of Report executions and resource consumption to identify resource hungry dashboard and analyse cause.
* Dashboard and Report view statistics over time.  Identify the most active KOs and who they are used by.
* Dashboard panel search scoring


