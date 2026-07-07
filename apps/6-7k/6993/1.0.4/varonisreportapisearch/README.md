#  Varonis Search & Reporting Add-on for Splunk
The Varonis Search & Reporting Add-on for Splunk provides integration with [Reporting API](https://help.varonis.com/s/document-item?bundleId=jlf1642695600232&topicId=qeq1531887398742.html&_LANG=enus). 
The key function is to integrate SPL custom command to query directly from the Splunk UI.

## Installation
The add-on can be installed manually via the .tgz file.

Reference Splunk documentation for [installing add-ons](https://docs.splunk.com/Documentation/AddOns/released/Overview/Installingadd-ons). 

## Splunk Permission Requirements
The add-on uses Splunk encrypted secrets storage, so admins require `admin_all_objects` to create secret storage objects and users require `list_storage_passwords` capability to retrieve secrets.

## Configuration

1. In Splunk, open the Add-on on Apps page -> Setup

![Configuring Varonis Search & Reporting](README_images/setup.png)

2. On the configuration > account tab:
- Enter the FQDN/IP the integration should connect to. (e.g.: `http://hostname/ReportAPI/api/`)
- Enter the Domain Qualified Username (e.g.: `DOMAIN\ReportUser`) for NTLM authentification.
- Enter the Password for NTLM authentification.
- Click Complete Setup

## SPL Command
### | alertedevents
The `| alertedevents` command allows executes a search for Audit events from User Access Log directly from Splunk's search bar.
This command actually represents the Report API query: `SELECT * FROM User_Access_Log WHERE Show_data_from = 'Audit_events' order by time desc`

Optional parameters are supported:

- **sam_account_name** - is to filter by SamAccountName_acting_object.
- **columns** - customize list of out fields (use * to retrieve all the fields). Default: Time,File_Server_Domain,Event_Status,Event_Type,Event_Description,Operation_By.
- **start_date** - optional alternative to the Splunk time picker. Note: if parameter is not provided make sure that Splunk time picker has not a Real-time or All time selection.
- **end_date** - optional alternative to the Splunk time picker. Note: if parameter is not provided make sure that Splunk time picker has not a Real-time or All time selection.


### | varonissearch

The `| varonissearch` command allows custom queries against the [Reporting API](https://help.varonis.com/s/document-item?bundleId=jlf1642695600232&topicId=qeq1531887398742.html&_LANG=enus) directly from Splunk's search bar. 

Required parameter:

- **query** - The Report API [query](https://help.varonis.com/s/document-item?bundleId=jlf1642695600232&topicId=dnv1531887397123.html&_LANG=enus) filter used to select events.

Make sure to `"`wrap the entire query in double quotes, and use `'`single quotes`'` inside`"` or double quotes `\"`escaped with a backslash`\"`, as shown in the following examples.




### Search Examples
### | alertedevents

Example 1:

`| alertedevents sam_account_name="Administrator"
`
Search for Audit events from User Access Log for specific SAM Account Name.

Example 2:
`| alertedevents start_date="2023-05-10 12:00:00" end_date="2023-05-25 12:01:00"
`

Search for Audit events from User Access Log for the time range provided in command params.

Example 3:

`| alertedevents sam_account_name="Administrator" columns="Time,File_Server_Domain,Event_status,Event_type,event_description,operation_by,distinguishedName_Acting_object" | rename distinguishedName_Acting_object as DN | table Time,File_Server_Domain,Event*,Operation_By,DN
`

Search for Audit events for specific SAM Account Name and return specific columns as a table.

### | varonissearch

Example 1:

`| varonissearch query="SELECT Time,File_Server_Domain,Event_status,Event_type,event_description,operation_by FROM User_Access_Log WHERE Show_data_from = 'Audit_events' and (time between '2023-05-10 12:00:00' and '2023-05-25 12:01:00') and SamAccountName_acting_object = 'Administrator' order by time desc"
`

Search for specific columns in Audit_events in User_Access_Log for a specific SAM Account Name for a given time range. Then return specific columns as a table.

![varonissearch example 1](README_images/varonissearch_ex1.png)

Example 2:

`| varonissearch query="SELECT * FROM User_Access_Log WHERE Show_data_from = 'Audit_events' and (time between '2023-05-10 12:00:00' and '2023-05-25 12:01:00') and SamAccountName_acting_object = 'Administrator' order by time desc" | rename distinguishedName_Acting_object as DN | table Time,File_Server_Domain,Event*,Operation_By,DN
`

Select all columns in for Audit_events in User_Access_Log for a specific SAM Account Name for a given time range. Then return specific columns as a table.

![varonissearch example 2](README_images/varonissearch_ex2.png)


