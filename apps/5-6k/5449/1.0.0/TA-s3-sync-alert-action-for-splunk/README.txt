*********************************************************************************************************************************************************
Add and Manage AWS accounts
*********************************************************************************************************************************************************
Perform the following steps to add an aws account:

*	In the Splunk Web home page, click S3 sync Alert Action For Splunk in the left navigation bar.
*	Click Configuration in the app navigation bar. The add-on displays the Account tab.
*	Click Add.
*	Name the AWS account. You cannot change this name once you configure the account.
*	Enter the Key ID and Secret Key credentials for the AWS account that the Splunk platform uses to access your AWS data. The accounts that you configure must have the necessary permissions to access the AWS data that you want to collect.
*	Click Add.
*	Edit existing accounts by clicking Edit in the Actions column.

Note: Delete an existing account by clicking Delete in the Actions column. You cannot delete accounts that are associated with any inputs, even if those inputs are disabled. To delete an account, delete the inputs or edit them to use a different account and then delete the account.

*********************************************************************************************************************************************************
Add an Alert Action S3 sync
*********************************************************************************************************************************************************
Perform the following steps to add an Alert with toggle action 'S3 sync':

*	In the Splunk Web home page, click 'Searches, reports and alerts' under Settings.
* 	Clone the default Alert template 'Test Alert'
*	Enter the Title in Clone Alert popup. Clone the permissions and click on Clone button.
*   For the newly created Alert, click on the Edit dropdown and select Edit Alert. 
*	Enter the search string in the Search field.
*	Set Permissions and Trigger Conditions as per requirements.
* 	Under the Trigger Actions 'S3 Sync' enter the required parameters.
*	Select the Account Name from the AWS Accounts configured.
*	Enter the AWS Region, Bucket name, Prefix of the file name and Filename to be saved in the AWS S3.