# Splunk Technology Add-on for GoogleSCC

## OVERVIEW

- The Add-on typically imports and enriches data from Google SCC SDK, creating a rich data set ready for direct analysis or use in an App. The GoogleSCC Add-on for Splunk will provide the below functionalities:
	- Collect sources data, findings data, assets data and audit logs from Google SCC SDK and store in Splunk indexes.
	- Categorize the data in different sourcetypes.
	- Parse the data and extract important fields

- Author - Google, Inc.
- Version - 2.0.3
- Prerequisites:
	- If installing Add-on in a Non-Cloud Environment, Users need to provide [Service Account JSON](https://cloud.google.com/docs/authentication/getting-started) which has the IAM permissions to configure the account.
	- If installing Add-on in a Non-GCP-Cloud (AWS, Azure) Environment, Users need to provide [Workload Identity Federation Credentials JSON](https://cloud.google.com/iam/docs/configuring-workload-identity-federation) and make sure the account linked with the VM has all the IAM permissions.
	- If installing Add-on in GCP-Cloud Environment, Make sure the Service account linked with the VM has all the IAM permissions.
	- Google SCC Organization Id for account configuration.
	- Google SCC Subscription for data collection.
- Compatible with:
	- Splunk Enterprise version: 10.4.x, 10.2.x, 10.0.x, 9.4.x and 9.3.x
	- OS: Linux, Windows
	- Browser: Chrome, Firefox

## Permission For Service Account
### For CAI creating Feed and fetching data of Assets

- Cloud Asset Owner (roles/cloudasset.owner)

### For SCC fetching data using api and creating Notification config

- Organization Viewer (on organization level)
- Security Centre Admin Viewer (on organization level)
- Security Center Notification Configurations Editor (roles/securitycenter.notificationConfigEditor)

## RECOMMENDED SYSTEM CONFIGURATION

- Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This Add-On can be set up in two ways:

1. Standalone Mode: 
    - Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.
2. Distributed Environment: 
    - Install Add-on on search head and Heavy forwarder (for REST API).
    - Add-on resides on search head machine need not require any configuration here.    
    - Add-on needs to be installed and configured on the Heavy forwarder system.    
    - Execute the following command on Heavy forwarder to forward the collected data to the indexer.
      `$SPLUNK_HOME/bin/splunk add forward-server <indexer_ip_address>:9997`
    - On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
    - Add-on needs to be installed on search head for CIM mapping

## Upgrade to v2.0.3
- Follow the steps mentioned below in order to upgrade your Google SCC Add-On for Splunk to v2.0.3:

    - Disable all the existing inputs.
    - Install the Google SCC Add-On for Splunk v2.0.3 by following the below steps :
        1. From the UI navigate to `Apps->Manage Apps`.
        2. In the top right corner select `Install app from file`.
        3. Select `Choose File` and select the App package file.
        4. Select `Upload` and follow the prompts.
    - Restart the Splunk if prompt.
    - Go to Google SCC Add-on for Splunk and navigate to the Configuration section.
    - Add the account by providing required details.
    - Edit all the inputs and follow below steps: 
        1. Enter Subscription name.
        2. Select the configured account in the Google SCC Account dropdown.
        3. Save the input.
    - Enable the inputs.

## INSTALLATION

Follow the below-listed steps to install an Add-on from the bundle:

- Download the App package.
- From the UI navigate to `Apps->Manage Apps`.
- In the top right corner select `Install app from file`.
- Select `Choose File` and select the App package.
- Select `Upload` and follow the prompts.

OR

- Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## CONFIGURATION

- From the Splunk Home Page, click on GoogleSCC Add-on for Splunk and navigate to the Configuration section.
- In the Google SCC Account tab, Provide the below required details:
    - Name
    - Service Account JSON (On Non-Cloud environment)
    - Credential Configuration (On AWS, Azure cloud environment)
    - Organization Id
- If all the details are correct, an Account is created.
- To use a proxy as part of the connection to Google SCC, go to the Proxy tab in the Configuration section and provide the required details. Don't forget to check the Enable option.
- To configure the Log Level, go to the Logging tab.
- Now go to the Input section for creating modular input.
- Click on the `Create New Input` button to configure a new Input.

### GoogleSCC Sources Input

- Enter the below required details: 
    - Name (To uniquely identify input in Splunk), 
    - Interval (Minimum and Default Value is 300s and Maximum Value is 900s), 
    - Index,
    - Google SCC Account
- click on `Add` to save the configuration.
- If all the details are correct, Input is created.
- To manage the Modular Inputs, navigate to the Inputs section.
- User can edit, delete, disable/enable and clone Modular Input by selecting specific Action.

### GoogleSCC Findings Input

- Enter the below required details:
	- Name (To uniquely identify inputs in Splunk),
	- Interval (Minimum and Default Value is 300s and Maximum Value is 900s), 
	- Index,
	- Google SCC Account,
	- Findings Subscription Name (created on GCP under your project), 
	- Maximum Fetching (maximum fetch limit to pull findings from GoogleSCC api, Minimum and Default Value is 500 and Maximum Value is 5000) 
- Click on `Add` to save the configuration.
- If all the details are correct, Input is created.
- To manage the Modular Inputs, navigate to the Inputs section.
- User can edit, delete, disable/enable and clone Modular Input by selecting specific Action.

### GoogleSCC Assets Input

- Enter the below required details:
	- Name (To uniquely identify inputs in Splunk),
	- Interval (Minimum and Default Value is 300s and Maximum Value is 900s), 
	- Index, 
	- Google SCC Account,
	- Assets Subscription Name (created on GCP under your project), 
	- Maximum Fetching (maximum fetch limit to pull findings from GoogleSCC api, Minimum and Default Value is 500 and Maximum Value is 5000) 
- Click on `Add` to save the configuration.
- If all the details are correct, Input is created.
- To manage the Modular Inputs, navigate to the Inputs section.
- User can edit, delete, disable/enable and clone Modular Input by selecting specific Action.


### GoogleSCC Audit Logs Input

- Enter the below required details:
	- Name (To uniquely identify inputs in Splunk),
	- Interval (Minimum and Default Value is 300s and Maximum Value is 900s), 
	- Index,
	- Google SCC Account,
	- Audit Logs Subscription Name (created on GCP under your project), 
	- Maximum Fetching (maximum fetch limit to pull findings from GoogleSCC api, Minimum and Default Value is 500 and Maximum Value is 5000) 
- Click on `Add` to save the configuration.
- If all the details are correct, Input is created.
- To manage the Modular Inputs, navigate to the Inputs section.
- User can edit, delete, disable/enable and clone Modular Input by selecting specific Action.

## TROUBLESHOOTING

### The input or configuration page is not loading.

- Check log file for possible errors/warnings: `$SPLUNK_HOME/var/log/splunk/splunkd.log`

### Data is not getting collected in Splunk

- Check the log file related to data collection is generated under `$SPLUNK_HOME/var/log/splunk/ta_googlescc_<input>.log`.
- If there is credential related error in the log then reconfigure the creds.
- To get the detailed logs, in the Splunk UI, navigate to GoogleSCC Add-on For Splunk. Click on Configuration and go to the Logging tab. Select the Log level to DEBUG.
- Disable/Enable the input to recollect the data.
- Check the logs. They will be more verbose and will give the user insights on data collection.
- Check by pulling data to your subscription id under your project on GCP. (In case of assets, findings and audit logs data).

### Unable to detect GCP, AWS or Azure cloud instances in the Add-on UI

- If the Add-on is installed on AWS or Azure instances and UI is not able to auto detect the instance make sure that `$SPLUNK_HOME/etc/apps/TA_GoogleSCC/local/ta_googlescc_settings.conf` is properly configured with following values and Splunk is restarted after the changes.  
```
[additional_parameters]
scheme = http
```
    
- Make sure that the KV Store is enabled on the Splunk. [reference](https://docs.splunk.com/Documentation/Splunk/8.2.5/Admin/TroubleshootKVstore)

### Events are mismatching of assets and findings

- Make sure that project id is same for the assets and findings input.

## UNINSTALL ADD-ON

- To uninstall add-on, user can follow below steps: 
    - SSH to the Splunk instance -> Go to folder apps($SPLUNK_HOME/etc/apps) -> Remove the TA_GoogleSCC folder from apps directory -> Restart Splunk

## COPYRIGHT INFORMATION

(C) 2026 Google

## SUPPORT

- Support Offered: Yes
- Support Hub: https://cloud.google.com/support-hub

## RELEASE NOTES

### Version 2.0.3
- Eliminated the additional API call associated with each Input invocation.
- Bumped the minimum required Python version to 3.13 as per Splunk standards.

### Version 2.0.2
- Updated the account validation code to fetch only active findings.

### Version 2.0.1
- Updated Python SDK to v2.1.0.

### Version 2.0.0
- Added support for account creation for multiple organizations.

### Version 1.0.0

- Added support for Data Collection of Sources, Findings, Assets and Audit logs.
- Added support of CIM v5.0.0 for Audit logs events.
- Added support for Data Collection on cloud instances (GCP, AWS, Azure).

## Binary file declaration

- google_auth - This binary file is provided along with google module and source code for the same can be found at https://pypi.org/
- googleapis_common_protos - This binary file is provided along with google module and source code for the same can be found at https://pypi.org/
- google_api_python_client - This binary file is provided along with google module and source code for the same can be found at https://pypi.org/
