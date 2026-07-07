Domain Controller (DC) Monitoring App
Overview:  -
In today’s world protecting Domain Controllers is a necessity, as it contains a highly classified data. So, it needs to be monitored as who is executing what activities in order to keep it in check.
Domain Controller (DC) Monitoring App provides you the security, that is needed to protect your Domain Controllers. The main objective of this app is to track the changes which can be highly volatile. This app gives proper insights with the help of inbuilt dashboards /alerts/reports.
To be able to use this application, you need windows “Security” and “PowerShell” logs getting ingested in Splunk.

Note:  -“Group Policy Audit” dashboard uses SA-LDAP to fetch Group policies name from Active Directory. So, You need to install & Configure the SA-LDAP application on your Search Head, to get the “Group Policy Audit” data.

Installation and Configuration: - 
Download and install the App from Splunkbase on Splunk Search Head.
After Installation, just edit the index in “Domain-Controller-Security-Index” Macro with the index where you are getting your DC logs. And edit “domain” macro with your domain.
Edit Macro “Domian-user” with the index where user’s data is getting ingested.
After Doing this, Data will start flowing in the Application as expected.


Dashboards: - 
1.)	Remote Access Success and Failed.
a.	The Dashboard provides information regarding remote access to your Domain Controllers.
2.)	Users Modified
a.	This Dashboard provides details regarding any changes done on users, Such as Enable /disable etc.
3.)	Restricted Logins
a.	This Dashboard provide information of disabled/lock user accounts trying to access your Domain Controller.

4.)	CMDs Executed
a.	This Dashboard provides information regarding the commands executed on Domain Controllers.
5.)	Group Policy Audit
a.	 This dashboard provides you the information related to the Group Policies.
6.)	Local Account Logins
a.	This Dashboard provides you information regarding the local account logins on all systems.

Reports: -
1.)	Asset_Identity_Report
a.	This report populates a alert with User as User’s systems information.
2.)	CMDs Executed
a.	This report gives information on CMDs executed.
3.)	Domain Controller List
a.	It gets Domain Controller list from data.
4.)	Failed RDP Sessions
a.	Gives us information regarding Failed RDP
5.)	GPO List Name
a.	Provides us a lookup for GPO Name list
6.)	Group Policy Changed
a.	Provides us information regarding Group policy changes
7.)	Restricted Logins Report
a.	Gives us a report on Restricted logins.
8.)	Successful RDP Sessions
a.	This report provides us information regarding successful RDP
9.)	Total User’s List
a.	Get’s total user list in a lookup
10.)	Users Audit Report 
a.	This gives us audit report regarding Any changes made to user’s account
Alerts: - 
1.)	Audit – Avo User Modified
a.	This alert provides a details regarding user account changes
2.)	Audit – Commands Ran on AD/DC
a.	This alert provides us details on CMD’s executed.
3.)	Audit – Failed RDP Sessions
a.	This alert provides details on Failed RDP Sessions.
4.)	Audit – Group Policy Changed
a.	This Alert Provides details on Group policy audit
5.)	Audit – Local account Logins
a.	This alert provides details on Local account logins.
6.)	Threat – Logins from Disabled account
a.	This alert gives information on Disabled account trying to logins
7.)	Threat – Logins from Locked Account
a.	This Alert Gives information on Locked account logins


# Binary File Declaration
# Binary File Declaration
