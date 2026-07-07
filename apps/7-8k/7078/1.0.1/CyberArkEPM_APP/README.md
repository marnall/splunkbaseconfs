# EPM Dashboards

## Description

CyberArk EPM dashboard is a powerful tool for your EndPoints having CyberArk EPM agent installed on it 
It will provide you with out of the box dashboards related to event managemnt , policies and Computers as well as Policy audit events

EPM Dashbaord App is built by using the Splunk Add-on for CyberArk EPM , link can be found below:
https://splunkbase.splunk.com/app/5160

Also make sure that when configuring the Splunk Add on for CyberArk EPM inputs to use the below names :

InboxEvents for Inbox Events Input 
PoliciesandComputers for Policies and Computers Input
PolicyAuditEvents for Policy Audit Events Input

Note:
need to create an index called epm 

## Installation

To install Your Splunk App Name, follow these steps:

Simply download the App :) 

## Details 

After installation, you can use Your Splunk EPM Dashboard to monitor :

1. Event management alerts : You will find dashboards that shows you , the Top application running on your endpoint s, applications running with time , application source types , 
Top Event types ( Elevation REquest , Ransomware , Attach attempt,etc..), in addition to Source type event summary and windows event summary 

2. Policies and Computer : in these dashboards yoou can easily identify endpoints type by time , endpoint status by time , total number of Agent installed as well as the Agent Version installed ,
Also you will be to see  list of computers(Inventory status) , as well as a number and a list of created policies on all of your endpoints 

3. Policy Audit Events : In these OOB dashboards you can find publisher Usage Statistics , percantahes of Policy execution , Nb of poilices executed by time plus a list of application by policy 


EPM Dashbaord App is built by using the Splunk Add-on for CyberArk EPM , link can be found below:
https://splunkbase.splunk.com/app/5160

Also make sure that when configuring the Splunk Add on for CyberArk EPM inputs to use the below names :

InboxEvents for Inbox Events Input 
PoliciesandComputers for Policies and Computers Input
PolicyAuditEvents for Policy Audit Events Input

## System Requirements

This App was built on Splunk Enterprise
Version: 9.0.5


## Release Notes

### Version 1.0.1 (October 13, 2023)
