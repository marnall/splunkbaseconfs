### Overview

#### About ‘orgSecure’

| Author | Khyati Majmudar |
| --- | --- |
| App Version | 1.0.0.0 |
| Vendor Products | None |
| Has index-time operations | false |
| Create an index | yes |
| Implements summarization | Implements Data Model |

##### Secure your Organisation from Threats Within

‘orgSecure’ is an Splunk based Analytics Solution to detect Insider Threats and monitor User Activities. 

Key Feature:
Key Feature:
* Detect Deviation in User Behaviour based on configurable Baseline Envelop of Historic Data
* Detect Anomalies through User Login/Logoff patterns, Out of Office Hours & Weekend usage.
* Detect Data Breaches through Data Transfer outside organisation through external sources like Wikileaks, File Sharing Sites and emails to public domain
* Detect Disgruntled employees who search for Jobs on Job portals
* Detect Abnormal Asset usage of employees like irregular / suspicious PC access, malicious softwares and abnormal Removable Media usage.
* Monitor User Profile through Hierarchy Analysis and Psychometric Tests
* Monitor User Usage through a unified view of different sources in a single window to get patterns out of the chronological events
* Monitor Critical Assets: PC - Through powerful visualization, understand who uses the PC as well as the activities performed
* Monitor Critical Assets: Files - Through powerful visualization, understand who accesses critical & confidential files, copies or emails them

##### Scripts and binaries

None used

#### Release notes

##### About this release

Version 1.0.0: Initial Version

Version 1.0.0 of the ‘orgSecure’ is compatible with:

| Splunk Enterprise versions | Splunk Enterprise 6.0.x or later. |
| --- | --- |
| Platforms | Platform independent |
| Vendor Products | None |
| Lookup file changes | None Required |


##### Known issues

No Known Issues

##### Support and resources

**Questions and answers**

Please email us: khyati.ninad@gmail.com for any Questions or Support required.

**Support**

Please email us: khyati.ninad@gmail.com for any Questions or Support required. Expected resolution time is 2 days


## INSTALLATION AND CONFIGURATION

### Hardware and software requirements

#### Hardware requirements

‘orgSecure’ supports all the server platforms in the versions supported by Splunk Enterprise.
 

#### Software requirements

No Extra Software are required.

#### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.


#### Installation steps

To install and configure this app on your supported platform, follow these steps:

1.	Click Download on this page. The orgSecure.tar.gz installer file downloads to your computer.
2.	Log into Splunk Web.
3.	Click Apps > Manage Apps.
4.	Click Install App from File.
5.	Upload the orgSecure.tar.gz installer file.
6.	Restart Splunk.



## USER GUIDE

### Key concepts for ‘orgSecure’

Key to detect Threats is Active Monitoring and Machine Intelligence to detect anomal user behaviour. This can be achieved by creating a Baseline envelop which defines the expected usage of the user. This could be based on either historical data of user or the data of his colleagues of his department. It may be possible that a user may be excessively using Job portals if he is from HR but if envelop is configured correctly, it will not be detected as a abnormal behaviour since it is 'normal' for him.

In order to achieve this, orgSecure uses complex statistical techniques to create baseline envelops for users which determines their normal usage patterns. Any deviation from the envelops for consecutive periods are reported and should be investigated. Also, comprehensive dashboards and visualizations are provided to actively monitor user and asset activities.

Key Inputs to the application are:
1.	Email
2.	Web Activity
3.	Login Logoff Logs
4.	Device Access Logs
5.	Removable Media Usage Logs

You can configure Alerts for any unusual Activities

### Data types

This app provides the index-time and search-time knowledge for the following types of data:

**Load Data**

Below are the key SourceTypes:
1.	orgsecure:http
2.	orgsecure:email
3.	orgsecure:device
4.	orgsecure:logon
5.	orgsecure:file

They are mapped as per CERT DARCA Data. Details found at:
URL : https://www.cert.org/insider-threat/tools/index.cfm

In case of any different data structure, you will have to modify the dashboard and report queries.


**Lookup**
Sample Lookups are provided under <lookup> folder. This needs to be updated with the details of your organisation. 

Lookups are:
•	LDAP: Employee Data of your employees
•	JobDomain: enter sites to monitor which are under Job portal category
•	SuspiciousDomain: enter sites to monitor which are suspicious and threat to organisation. Like Wikileaks, file sharing sites, etc
•	SuspiciousFiles: Enter software names which are to be monitored and which users should not access. E.g. keylogger
•	Psychometric: Enter psychometric test results of employees


### Configure ‘orgSecure’

By default, ‘orgSecure’ does not come with any File Inputs. In order to add any Folders to monitor for input logs,
1.	Go to Settings > Data Inputs
2.	Click on Files and Directories
3.	You can add Directories to monitor where you can place your financial documents. Save it with respective SourceType
4.	You can also configure direct import of data as per Splunk best practices

In order to perform baseline analysis, select baseline envelop to be in history (say last 3 months) and select the period under analysis. The respective screens with show the abnormal behaviour as compared to the baseline envelops.


### Example Use Case ###
Insider Threats is a major cause of concern for various organisations today. With a robust IT Infrastructure, organisations do fairly well to defend against any external intrusions. However, employees who have access to data from within the organisation remains a threat to confidential and critical data to business. 
With Advanced Analytics & monitoring, it is possible to detect any anomaly and take appropriate measures in time. orgSecure is an Splunk based Analytics Solution to detect Insider Threats and monitor User Activities. 
User behaviour, emails, Web Activity, File access and removable media access can be monitored through orgSecure and obtain details on threats and monitor user & asset activities
