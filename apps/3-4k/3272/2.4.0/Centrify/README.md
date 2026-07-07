# About this App

Centrify App for Splunk is aimed at providing insight into Centrify Infrastructure Services Audit Trail events via various dashboards and reports. This app requires Centrify Add-on for Splunk.

* Author - Centrify Corporation
* Version - 2.4.0
* Build - 100
* Creates Index - False
* Prerequisites - This application is dependent on Centrify Add-on for Splunk
* Compatible with:
	* Splunk Enterprise version: 6.4.x, 6.5.x, 6.6.x, 7.0.x and 8.0.x
 	* OS: Platform independent

# Requirements

* Splunk version 6.2 and above

# Recommended System Configuration

* Splunk forwarder system should have 4 GB of RAM and a quad-core CPU to run this app smoothly.

# Installation of App

* This app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.

# Configuration of App

* There are a couple of alerts and reports configured in this app. User/Admin needs to add appropriate email addresses to receive the alerts and reports on mail.

# Compatibility with Splunk Add-on for Windows and Splunk Add-on for *nix

* It is possible that user is already using Splunk Add-on for Windows and collecting Windows application logs on indexers.
* In this case, he should already have Splunk forwarder along with Splunk Add-on for Windows is installed on his Windows machine.
* Since Centrify logs are already part of the Windows application logs, the user does not have to install anything additional.
* He should be able to see the Centrify data directly on the indexers.
* Similarly if the user is already using Splunk Add-on for Unix and sending specific Unix logs to indexers, he should already have Splunk forwarder along with Splunk Add-on for Unix installed on Unix machine.
* User can modify the inputs.conf and add Centrify specific log directory and start forwarding that data to the indexers.

* Note that Data collection stanzas in Centrify Add-on for Splunk will remain disabled because we are not using them to collect data. In this case, Centrify Add-on for Splunk is mainly used for field extractions and data normalization.

# EULA

* Please check End User's License Agreement at https://www.centrify.com/eula-siem

# Release Notes

* Version 2.4.0
  * Tested Compatiblity with Splunk 8.0.x

* Version 2.3.0
	* Updated macro definition to support new CentrifyEventIDs updated Centrify version 2017.2 and 2017.3 and deprecated from Centrify version 2017.1.
	* Bug fix related to drill-down in panels "Role Activity by Name Over Time - Windows only" and "Zone Activity by Name Over Time - Windows only" in dashboard "Admin Activity".
	* X-axis labels in timecharts changed from _time to Time.

* Version 2.2
	* Fixed typo in the name of panel "Systems with Privilege Activity".
	* Updated query of "User Login activity- Lookup Gen" to populate lookup by latest login time.
	* Changed panel and dashboard titles as per the customer feedback.

# Support Information
    
    * Community supported. You can use following url to ask questions.
         URL: https://answers.splunk.com/app/questions/3272.html 
# Savedsearches
This application contains two saved searches.

* Machine Login activity - Lookup Gen
This saved search is used to populate "machine_login_activity" lookup.

* User Login activity- Lookup Gen
This saved search is used to populate "user_login_activity" lookup.

# Reports

This application contains five reports. All these reports are scheduled to report which runs weekly, Saturday at 0:00. An email containing report results in pdf is sent as an action after the creation of the report.

* Anomalies happened over the week
This report query populates data for the anomalies happened throughout the previous week.

* Machines not logged in over the week
This report query populates data for the machines not logged in throughout the previous week.

* Most Actively used Servers over the week
This report query populates data for the most actively used servers throughout the previous week.

* Most Privileged Users over the week
This report query populates data for the users with most privileges throughout the previous week.

* Users not logged in over the week
This report query populates data for the users who didn't log in throughout the previous week.

# Alerts

This application contains five alerts. All these alerts are scheduled to run at every day at 00:00 hrs. Each alert will generate events in Triggered Alerts and also has an associated email action. This action will require EMAIL server to be configured.

* Audited Node Down in Last day
This Alert gives information about Audit Agent machine gone down during last one day.

* Collector Service Down in Last day
This Alert gives information about collector service going down during last one day.

* Multiple Login Failures in Last day
This Alert gives a count f login attempt failures by the users on machines during last one day.

* Privileged Command Failures in Last day
This Alert gives a list of privileged command during last one day.

* Privileged Activity Failures in Last day
This Alert gives a list of Privileged Activity during last one day.


Copyright © 2021 Centrify Corporation