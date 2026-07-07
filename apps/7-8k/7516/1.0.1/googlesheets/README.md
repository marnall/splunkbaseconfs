[comment]: # "Auto-generated SOAR connector documentation"
# Google Sheets

Publisher: Splunk Community  
Connector Version: 1.0.1  
Product Vendor: Google  
Product Name: Google Sheets  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.2.1  

This app allows various file manipulation actions to be performed on Google Sheets

This app requires a pre-configured service account to operate. Please follow the procedure outlined below.

# Step 1: Create a project
1. Go to Google Cloud and sign in as a super administrator. If it's your first time signing in to the console, agree to the Terms of Service.
2. Click IAM & Admin > Manage Resources. You might have to click Menu first.
3. At the top, click Create Project and enter a project name.
4. (Optional) To add the project to a folder, for Location, click Browse, navigate to the folder, and click Select.
5. Click Create.
6. By default, only the creator of the project has rights to manage the project. To ensure the project can be maintained if the creator leaves the organization, you should assign at least one other person the role of Project Owner. For details, go to [Manage access to projects, folders, and organizations](https://cloud.google.com/iam/docs/granting-changing-revoking-access).

# Step 2: Turn on the APIs for the service account
1. Go to Google Cloud Console and select the project you created above in Step:1 from the dropdown list on the top.
2. Click APIs & Services > Library. You might have to click Menu first.
3. For each API you require (below), click the API name and then Enable:
    1. Google Sheets API
    2. Identity and Access Management (IAM) API
    3. Google Drive API

    **Tip**:If you can't find the API, specify the API name in the search box.

# Step 3: Create the service account
1. Click APIs & Services > Credentials. You might have to click Menu first.
2. Click Create Credentials > Service account.
3. For Service account name, enter a name for the service account.
4. (Optional) For Service account description, enter a description of the service account.
5. Click Create and Continue.
6. Click Done > Save.
7. Select the service account you just created and note down the email ID. You'll need it later while creating an asset for the connector (service_account_email).
8. At the top, click Keys > Add Key > Create new key.
9. Make sure the key type is set to JSON and click Create.

    You'll get a message that the service account's private key JSON file was downloaded to your computer. Make a note of the file name and where your browser saves it. **You'll need it later while creating an asset for the connector (service_account_credentials)**.

10. Click Close.
11. At the top, click Permissions.
12. Click Grant Access
13. In Add Principals field, enter the service account email ID.
14. In Assign roles select Service Account Admin
15. If the google sheet you are trying to modify is not created from the same service account then open the sheet > Share > Enter the service account email ID > give editor access and click on done before using this app.

### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Google Sheets asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**service_account_email** |  required  | string | Enter service account email id
**service_account_credentials** |  required  | password | Paste your service account credentials here

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[add new rows](#action-add-new-rows) - Use this action to add new rows to the sheet  
[create spreadsheet](#action-create-spreadsheet) - Create a new spreadsheet and share with users  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'add new rows'
Use this action to add new rows to the sheet

Type: **generic**  
Read only: **False**

This action can be used to append new rows to the sheet.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**google_sheet_id** |  required  | ID of the google sheet. This can be found in the URL | string | 
**rows** |  required  | List of list of rows to be added. Example: [["row_1_col_1_data","row_1_col_2_data"],["row_2_col_1_data","row_2_col_2_data"], ...] | string | 
**sheet_name** |  required  | Name of the sheet. This can be found in the bottom tabs of the google sheet | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.google_sheet_id | string |  |  
action_result.parameter.rows | string |  |  
action_result.parameter.sheet_name | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'create spreadsheet'
Create a new spreadsheet and share with users

Type: **generic**  
Read only: **False**

This action will create a new google sheet in the service account's root and share it with the users.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_name** |  required  | Enter name of the spreadsheet | string | 
**user_emails** |  required  | Give a comma seperated list of email IDs to share the file with | string | 
**permission_type** |  required  | Select permission type to give to users | string | 
**role** |  required  | Select role to be assigned | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.file_name | string |  |  
action_result.parameter.user_emails | string |  |   user@sample.com  otheruser@email.com 
action_result.parameter.permission_type | string |  |   user  group 
action_result.parameter.role | string |  |   writer  reader  commenter 
action_result.status | string |  |   success  failed 
action_result.data.\*.spreadsheetId | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |  