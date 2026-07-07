LT Auditor App for Splunk 
version 1.0
Copyright (C) 2017 BLUE LANCE Inc.

OVERVIEW
--------------
The LT Auditor+ App for Splunk enables seamless integration of BLUE LANCE’s LT Auditor+ suite of products into Splunk Enterprise. The App is optimized to ingest data from LT Auditor+ and has Intelligent dashboards with drilldown capabilities to provide a complete view of change activity on Active Directory, Group Policy, Servers, File Shares, Endpoints, USB Flash Drives in an organization. The key benefits of using the LT Auditor+ App for Splunk are:

* Provides accountability by producing a complete audit trail like showing who did what from where and when for changes to user identities, policies and access to critical files;
* Gain high fidelity in audits by reducing noise and clutter in Windows event logs;
* Improved quality by de-duplicating data with advanced filtering capabilities;
* Enhance efficiency by providing data in key value pairs allowing for faster indexing and searching.

LT Auditor+ App for Splunk includes the capability to possibly detect data exfiltration attempts along with real time detection of potential ransomware attacks.

Installation Instructions:

Installation requires two major steps:
1. Installation and configuration of LT Auditor+ on Windows servers to transfer audit data to Splunk;
2. Installation of the LT Auditor+ App for Splunk

LT Auditor+ can be downloaded from the BLUE LANCE website www.bluelance.com
The app can be downloaded from splunkbase where instructions have been provided.
 

 
Documentation:
  
  Requirements
  	The LT Auditor+ App for Splunk requires Splunk Enterprise 6.5 and above.
	Please review documentation on LT Auditor+ installation to review minimum requirements


  DASHBOARDS
  ------------------

 [Home]

The Home dashboard that provides a summary of all LT Auditor+ activity ingested by Splunk and displays the following notables:
* Audited Events ? Count of total audited events for specified time range.
* Audited Users ? Count of total users audited for specified time range.
* Audited Agents ? Number of LT Auditor+ agents sending data to Splunk.

Clicking on any of the LT Auditor+ Audited Modules listed will take the user to new dashboard for specified activity. The following dashboards are accessible:

1. Active Directory
2. File/Folder
3. Group Policy
4. Logon
5. Health Check

[Active Directory]
The Active Directory dashboard provides complete details of all Active Directory activity recorded with LT Auditor+.
     
This dashboard can be filtered based on the following criteria: 
1. Time Frame
2. Active Directory Objects
3. Active Directory Classes
4. Active Directory Attributes
5. Active Directory Attribute Values
6. Users
7. Nodes
8. Servers

The Active Directory dashboard displays the following notables:
1. Total Events - Count of all Active Directory events collected as per filter criteria. Clicking on this notable will generate a report of those events.
2. Objects - Count of distinct Active Directory objects modified per filter criteria. Clicking on this notable generates a table summary of these objects with column counts of users, nodes, servers and activity count as shown below. Clicking on any of the objects will generate a detailed report of changes on specified object.
3. Classes - Count of distinct Active Directory classes modified per filter criteria. Clicking on this notable generates a table summary of these classes with column counts of users, nodes, servers and activity count as shown below. Clicking on any of the classes will generate a detailed report of changes on specified class.
4. Users - Count of users that performed operations per filter criteria. Clicking on this notable generates a table summary of users with column counts of objects, nodes, servers and activity count as shown below. Clicking on any of the Users will generate a detailed report of changes made by specified user.
5. Nodes - Count of source node addresses of users that performed operations per filter criteria. Clicking on this notable generates a table summary of nodes with column counts of objects, users, servers and activity count as shown below. Clicking on any of the Nodes will generate a detailed report of changes made from specified node.
6. Servers - Count of host servers where changes occurred per filter criteria. Clicking on this notable generates a table summary of servers with column counts of objects, users, nodes and activity count as shown below. Clicking on any of the Servers will generate a detailed report of changes made on the specified server.


[Files/Folders]
The Files/Folders dashboard provides complete details of all file and folder activity recorded with LT Auditor+.

This dashboard can be filtered based on the following criteria: 
1. Time Frame
2. Users
3. Nodes
4. Servers
5. Filenames

The Files/Folders dashboard displays the following notables:
1. Total Events - Count of all Files/Folder events collected as per filter criteria. Clicking on this notable will generate a report of those events.
2. Users - Count of users that performed operations per filter criteria. Clicking on this notable generates a table summary of users with column counts of objects, nodes, servers and activity count as shown below. Clicking on any of the Users will generate a detailed report of changes made by specified user.
3. Nodes - Count of source node addresses of users that performed operations per filter criteria. Clicking on this notable generates a table summary of nodes with column counts of objects, users, servers and activity count as shown below. Clicking on any of the Nodes will generate a detailed report of changes made from specified node.
4. Servers - Count of host servers where changes occurred per filter criteria. Clicking on this notable generates a table summary of servers with column counts of objects, users, nodes and activity count as shown below. Clicking on any of the Servers will generate a detailed report of changes made on the specified server.
5. Failed Attempts - Count of all failed file activity collected as per filter criteria.





[Group Policy]
The Group Policy dashboard provides complete details of all Group Policy activity recorded with LT Auditor+.

This dashboard can be filtered based on the following criteria: 
1. Time Frame
2. GPO Name or Object
3. Attribute or GPO Attribute
4. Users
5. Nodes
6. Servers

The Group Policy dashboard displays the following notables:
1. Total Events - Count of all Group Policy events collected as per filter criteria. Clicking on this notable will generate a report of those events.
2. GPO Name - Count of distinct GPO objects modified per filter criteria. Clicking on this notable generates a table summary of these objects with column counts of users, nodes, servers and activity count as shown below. Clicking on any of the objects will generate a detailed report of changes on specified object.
3. Attributes - Count of distinct GPO Attributes modified per filter criteria. Clicking on this notable generates a table summary of these attributes with column counts of users, nodes, servers and activity count as shown below. Clicking on any of the classes will generate a detailed report of changes on specified class.
4. Users - Count of users that performed operations per filter criteria. Clicking on this notable generates a table summary of users with column counts of objects, nodes, servers and activity count as shown below. Clicking on any of the Users will generate a detailed report of changes made by specified user.
5. Nodes - Count of source node addresses of users that performed operations per filter criteria. Clicking on this notable generates a table summary of nodes with column counts of objects, users, servers and activity count as shown below. Clicking on any of the Nodes will generate a detailed report of changes made from specified node.
6. Servers - Count of host servers where changes occurred per filter criteria. Clicking on this notable generates a table summary of servers with column counts of objects, users, nodes and activity count as shown below. Clicking on any of the Servers will generate a detailed report of changes made on the specified server.


[Logon Server]
The Logon Server dashboard provides complete details of all login activity recorded with LT Auditor+.

This dashboard can be filtered based on the following criteria: 
1. Time Frame
2. Users
3. Nodes
4. Servers
5. Filenames

The Logon Server dashboard displays the following notables:
1. Total Events - Count of all Logon events collected as per filter criteria. Clicking on this notable will generate a report of those events.
2. Users - Count of users that performed operations per filter criteria. Clicking on this notable generates a table summary of users with column counts of objects, nodes, servers and activity count as shown below. Clicking on any of the Users will generate a detailed report of changes made by specified user.
3. Nodes - Count of source node addresses of users that performed operations per filter criteria. Clicking on this notable generates a table summary of nodes with column counts of objects, users, servers and activity count as shown below. Clicking on any of the Nodes will generate a detailed report of changes made from specified node.
4. Servers - Count of host servers where changes occurred per filter criteria. Clicking on this notable generates a table summary of servers with column counts of objects, users, nodes and activity count as shown below. Clicking on any of the Servers will generate a detailed report of changes made on the specified server.
5. Failed Logons - Count of all failed login events collected as per filter criteria. Clicking on this notable generates a table summary of user failed activity with column counts of nodes, servers and activity count as shown below. Clicking on any of the users will generate a detailed report of failed logon activity for specified user.

  

  SUSPICIOUS ACTIVITY
  -------------------

[Bulk Rename]
Ransomware attacks typically cause a lot of simultaneous rename operations as files get encrypted. This dashboard displays incidents where there have been more than 500 renames by the same user from the same node at the same time.

[Bulk Copy]
Data exfiltration occurs when malicious actors access large numbers of files at the same time. This dashboard displays incidents when more than 500 files were accessed by the same user, from the same node at the same time. 


[Excessive Failed Logins]
Excessive failed logon activity always needs to be investigated to ensure that an organization is not being attacked. This dashboard provides details on all logon failures and the type of failure.

[Account Lockout Activity]
This dashboard provides a summary of all account lockout activity and provides the source information of machines that caused the lockouts.

BEST PRACTICE

[Elevated Privileges]
This dashboard provides a quick view of privileges elevated for specified time frame. 

Privileges tracked are:

1. Group memberships to powerful groups
2. Active Directory permissions delegated
3. Group Policy permissions delegated
4. Linked Group Policies changed
5. Group Policy Filtering changes

 [System Access]
This dashboard provides a quick view access to the organization?s network that may require reviews. 

Access events tracked are:

1. Admin Logons
2. Generic ?Administrator? Logons
3. Remote Access
4. After Hour Logon activity


[Policy Changes]
This dashboard provides a quick view group policy modification critical for any organization. 

Policies tracked are:

1. Lockout Policy Changes
2. Password Policy Changes
3. System Policy Changes
4. Audit Policy Changes



 DATA INPUT
 ----------------
Data is sent by LT Auditor+ agent modules on Windows machines. Information can be sent directly on TCP port 1468 or via a Splunk forwarder on the Windows machine.

 INDEX
 --------
 All data is sent to an index called [lt_auditor_idx] that is created by the app. Data retention is set for 30 days.

 SPLUNK SOURCETYPES
 ------------------------------
Sourcetype over-ridding has been used to distribute data. By default, data generic_single_line is used but depending on the data it is overridden into the different source types listed below:

    [Active_Directory]
    Contains data related to active directory. Keyword for which is "ADA".

    [File_Audit]
    Contains data related to files and folders. Keyword for which is "FSA".

    [Group_Policy]
    Contains data for group policy. Keyword for which is "GPA".

    [Logon]
    Contains data for logon servers. Keyword for which is "LSA".

    [Health_Check]
    Contains data for Health check of the lt auditor agents. It gives stats for total, active, inactives agents.

More information

	For more information and to set up your trial or paid subscription,
	please contact support@bluelance.com.


SUPPORT
----------------------------
Email : support@bluelance.comPhone : +1 (800-856-2583).
Working hours : 8:30am - 5:30pm CST

