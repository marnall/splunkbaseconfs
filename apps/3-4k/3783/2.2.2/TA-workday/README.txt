The Workday Add-on for Splunk® enables you to automatically send a copy of user activity log and signon data from your Workday tenant into your Splunk account. This enables you to use Splunk to parse the log data to monitor for harmful activity in your tenant.

If you enable this functionality, a copy of your user and signon activity data will reside outside of Workday.

The Workday Add-on for Splunk is available on the Splunkbase site and is not part of the Workday Service. Follow the directions on Splunkbase to license and download the add-on.

Do these steps to set up Workday to send data to Splunk:

1. Create an Integration System User.
2. Register the add-on client in your tenant.
3. Retrieve client values for the add-on.
4. Enable your tenant to send data to Splunk.
5. Create Custom Signon Report
If the Workday Add-on for Splunk is not working as expected, please have a Workday Administrator in your organization create a case to receive assistance from Workday Support.

-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

*Create an Integration Systems User*

Create an Integrations Systems User and the associated Security Group and Policy.

1. Access the Create Integration System User task.
    User Name: Splunk_ISU
    Session Timeout Minutes: 0 (disable session expiration)
    Do Not Allow UI Sessions: Yes (select this checkbox)
2. Access the Create Security Group task.
    Type of Tenanted Security Group: Integration System Security Group (Unconstrained)
    Name: Remote Security Monitoring
3. Access the Edit Integration System Security Group (Unconstrained) task for the group you just created.
    Integration System Users: Splunk_ISU
4. Access the View Domain task for the domain System Auditing.
5. Select Domain > Edit Security Policy Permissions from the System Auditing related actions menu. (Note: You may have to select See More>Switch to Full Menu for 10 seconds to see edit Policy Permissions)
6. Add the group you created, Remote Security Monitoring to both tables:
    Report/Task Permissions table: View access
    Integration Permissions table: Get access
7. Access the Activate Pending Security Policy Changes task and activate the changes that you made.
For additional information, see Set Up Integration System User Security in Workday documentation.

-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

*Register the Add-on Client in your Tenant*

1. Access the the Register API Client for Integrations task and register the client.
    Client Name: Workday Add-on for Splunk
    Non-Expiring Refresh Tokens: Yes
    Scope: System
For additional information, see Register API Client for Integrations in Workday documentation.

-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

*Retrieve Client Values for the Add-on*

1. Access the View API Clients task, select the API Clients for Integrations tab and confirm these settings:
    Client Grant Type: Authorization Code Grant
    Access Token Type: Bearer
2. Copy and store these four values (the first two values are at the top of the page):
    Workday REST API Endpoint
    Token Endpoint
    Client ID
    Client Secret
3. Select API Client > Manage Refresh Token for Integrations from the Workday Add-on for Splunk related actions menu.
    Workday Account: Splunk_ISU
4. Select Generate New Refresh Token checkbox, then save that token.
5. Enter the values you saved into the add-on.

-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

*Enable your tenant to send data*
1. Access the Edit Tenant Setup - System task and ensure that the Enable User Activity Logging checkbox is selected.
2. Access the Edit Tenant Setup - Security task and ensure that the OAuth 2.0 Clients Enabled checkbox is selected
# Binary File Declaration
/Users/nilay.shah/Downloads/splunk/var/data/tabuilder/package/TA-workday/bin/ta_workday/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-workday/bin/ta_workday/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code

-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

*Create Custom Signon Report*
The Custom Signon Report provides information about successful and attempted signons from candidates within Workday. Follow the steps below to configure your Workday tenant to send these reports to Splunk.

1. Access Copy Standard Report to Custom Report task
    Standard Report Name: Candidate Signons and Attempted Signons
2. Click OK and the next page will pop up
    Name: Custom Signons and Attempted Signons Report
    Select "Optimized for Performance"
3. Click OK and the next page will pop up
    Data Source Filter: Workday System Account Signons in Range
    Under Share tab select "Share with specific authorized groups and users" and add Splunk_ISU to the Authorized Users field
    Under Advanced tab scroll to Web Services Options and select "Enable as Web Service"
    Under the Columns tab add these fields using the + button:
        -Operating System
        -Password Changed
        -Request Originator
        -SAML Identity Provider
        -Forgotten Password Reset Request
        -Multi-Factor Type
        -Is Device Managed
        -UI Client Type
        -Browser Type
        -Device is Trusted
        *You may also add other additional fields of interest
    Under the Column Heading Override column:
        Delete "ID" for field "Session ID"
        Delete "Candidate for Candidate Account" for field "System Account"
4. Click OK
5. Select Webs Service>URLs from Custom Signons and Attempted Signons Report related
    Note: Leave To Moment and From Moment as is. You will configure these parameters in the add-on's configueration
6. Click OK
7. Copy URL from JSON link (Right click>Copy URL). The URL should look like this:
    https://<workday_hostname>/ccx/service/customreport2/<tenant>/<accountname>/<reportname>/<tomoment>/<frommoment>/<format>/

In the Workday add-on in Splunk: 
8. Click on Create New Input > Signon Activity
    Store value  under Report URL
        Delete everything after <reportname>
    

NOTE: Additional security configurations may be necessary in order to allow the custom report to be accessed by the app. Consult with your Workday administrator to enable the right permissions for the Splunk_ISU.# Binary File Declaration
/Users/nilay.shah/Downloads/splunk/var/data/tabuilder/package/TA-workday/bin/ta_workday/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Users/nilay.shah/Downloads/splunk/var/data/tabuilder/package/TA-workday/bin/ta_workday/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/Users/nilay.shah/Downloads/splunk/var/data/tabuilder/package/TA-workday/bin/ta_workday/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Users/nilay.shah/Downloads/splunk/var/data/tabuilder/package/TA-workday/bin/ta_workday/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
