The SMTP dashboard for Splunk Enterprise, it provides custom Splunk searches and dashboards for Simple mail transfer protocol server logs. All dashboards have been highly optimized for fast performance and contain custom drill-downs. Use to gain visibility and add insights to your mail sever logs.SMTP server error codes details is also incorporated in the app.

Add-on Details:
The Simple Mail Transfer Protocol is a communication protocol for electronic mail transmission. That's why to send your messages with an email client or software you need first of all to configure the correct SMTP settings – in particular, the right SMTP address.
Overview
The Microsoft SMTP app for Splunk, it provides custom Splunk searches and dashboards for Simple mail transfer protocol server logs. All dashboards have been highly optimized for fast performance and contain custom drilldowns. Use to gain visibility and add insights to your mail sever logs. SMTP server error codes details is also incorporated in the app.
This app also provide monitoring for SMTP logs and helps to onboard logs into Splunk with  pre-existing sourcetype and monitoring stanza  to extract SMTP IIS logs in w3c Format.
Here we get two type of log SMTP daily email logs and BAD email logs.
          
Using this App:
Enable SMTP Server log settings:
SMTP log format selected is “W3C Extended Log File Format“ as W3C Extended format is a customizable ASCII format with a variety of different properties. You can log properties important to you, while limiting log size by omitting unwanted property fields. Properties are separated by spaces. Time is recorded as UTC.
Go to link for enabling SMTP server logging https://avotrix.com/docs/How_to_enable_logging_for_IIS_SMTP_server_in_windows-converted.pdf
Configuration and Installation:
Deployment Guide: 
Pre-requisite 

To enable logs from Microsoft IIS SMTP server , for steps follow given link.

This app contains monitoring stanza ,path can be edited as per specific path give by user for SMTP logs. Index we are using here is Infra . Although no indexes.conf is given in package it should be made by user only while installation.
If you are using some index other, then Infra edit macro smtp_index for dashboard population, also edit eventype "smtp_ip" and put client_ip as per your logs

•	Single Instance 
Install app here.

•	Distributed deployment 
Heavy Forwarder/Universal forwarder – Install app here. Enable monitoring stanza from inputs.conf (place index and add monitor path if not using standard)

Search Head – Install app here 



Sourcetype details:
smtp:iis:w3c – Getting  SMTP email transactions logs
ms:iis:Badmail – Getting SMTP bad email logs

App configuration Setup:
Please see Splunk's official documentation for the initial installation of the app. To use the dashboards, data must have been imported using the UF/HF from data server also configure timezone in props.conf indexer.

          
Dashboard:
On the dashboard, results can by filtered by Time range. Selecting a new option in this panel will automatically reload the all graphs
The very first row gives overview of daily count of Total, Outbound, Bounced and Erreneous  with a trend line , provided drilldwon in  panels
Outbound Email drilldown gives us details of mail sent to some recepient with other than permitted domain
Bounced Email drilldown gives us details of delivery failure
Error code generated while mail transaction will get captured with issue details. Drill down for error code time will give insights of failed mail
Error code statistics gives statstical data for all generated error codes
                
Reports - Existing schedule and triggering condition can be altered as per required
Daily report to collect Error code generated: This report runs daily on 00:00 AM and collects all the error code with details
Daily report to collect Outbound Email list: This report runs daily on 00:00 AM and collects details of all outbound email sent
Daily report to collect Bounced Email list: This report runs daily on 00:00 AM and collects details of all Bounced email
           
Alerts - Existing schedule and triggering condition can be altered as per required
Error code generated -Email failed: Triggers when Error code count is greater than 20, runs at every three hour
Outbound Email sent: Triggers when an outbound email sent is greater than 0, runs at every hour past 15 minutes
Bounced Email alert generated: Triggers when Bounced email count is greater than 20, runs at every three hour

About Microsoft SMTP app for Splunk
Author -Avotrix
App Version – 2.2.0
Has Index Time Extraction- Yes
Has Search Time Extraction- No

Release Notes
Version 2.2.0

Dashboard Queries  Read me updated 

Contact US
Email: support@avotrix.com
          
# Binary File Declaration
# Binary File Declaration
# Binary File Declaration
