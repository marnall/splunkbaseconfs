
## About this Article

This article provides the procedure to integrate Cyble Threat Intel application with Splunk. This integration helps users to access Cyble threat alerts and Indicators of Compromise (IoCs) in real-time, directly in Splunk platform, to speed up the remediation action.


## Pre-requisites

The pre-requisites for Splunk Integration are:

 1. Ensure that the latest version of Splunk Enterprise platform is installed
 2. Procure the Access Token from the Cyble Vision platform


### Install Splunk Enterprise

Follow the below steps to install Splunk Enterprise platform locally in the system:

 1. Access the Splunk web portal using the URL: https://www.splunk.com/
 2. Download the latest version of Splunk Enterprise Platform and install the application 

> **Note:** Refer [Splunk Documentation](https://docs.splunk.com/Documentation/Splunk) for more information.


### Procure Access Token

 Follow the below steps to procure an Access Token:

1. Login to the [Cyble Vision platform](https://cyble.ai/) using valid credentials
2. Navigate to **Utilities > Access APIs** in the left navigation pane and click **Alerts API v2** 
3. Click  **Generate API Key** Icon on the top right corner of the page
![1](./images/splunk/1.png)
4. Provide a suitable name in the pop-up and click **Generate**
![2](./images/splunk/2.png)
5. API key is displayed. Copy the generated API key


## Step1 : Installation

Follow the below steps to install Cyble Threat Intel application in Splunk:

1. Access Splunkbase using the URL: [https://splunkbase.splunk.com/](https://splunkbase.splunk.com/)
2. Search and select the **Cyble Threat Intel** application
![3](./images/splunk/3.png)
3. Click **Login to Download**
![4](./images/splunk/4.png)
4. Provide valid credentials in the Splunk login screen and download the application
5. Open the Splunk Enterprise platform
6. Click **Manage**
![5](./images/splunk/5.png)
7. Click **Install app from file**
![6](./images/splunk/6.png)
8. Select the downloaded Cybel Threat Intel application file(*.spl*) and click **Upload**
![7](./images/splunk/7.png)
9. Restart Splunk when prompted
 

## Step2 : Configuration

Indexes Setup

1. Open Splunk Web and navigate to the Settings menu.
2. Select Indexes from the dropdown menu. This will open the Indexes page.
3. On the Indexes page, click the New Index button to create a new index.
4. In the Index Name field, enter cyble_alerts for the first index.
5. Change the App dropdown value to Cyble Threat Intel to associate this index with the corresponding app.
6. Click Save to create the cyble_alerts index.
7. Repeat steps c–f and create another index with the name cyble_iocv2.
Follow the below steps to complete the integration process:

1. On the Splunk Enterprise platform, navigate to **Cyble Threat Intel** in the left navigation pane
![8](./images/splunk/8.png)
2. Click **Setup Page > Cyble Alerts Configuration**
![9](./images/splunk/9.png)
3. Provide the below information:

| Parameter | Description/Value |
|--|--|
| Name | Name of the Cyble Alert configuration |
| API key | API Key copied from Cyble Vision platform  |
| Days| Number of preceding days of alerts to include in the fetch. The value should be between 1 and 15|
| Interval | Polling Interval |
| Enable Proxy | **Enable** this option for Proxy configuration |
| Proxy URL | Proxy server URL|
| Proxy Username | Username of the Proxy configuration |
| Proxy Password | Password of the Proxy configuration |

![10](./images/splunk/10.png)

4. Click **Submit**
5. Repeat the above steps to complete configuration for Cyble IOC by navigating to **Setup Page > Cyble IOC Configuration**




## View Alerts/IoCs

1. On the Splunk Enterprise platform, navigate to **Cyble Threat Intel** in the left navigation pane
 ![8](./images/splunk/8.png)
2. Navigate to **Cyble Alerts > Executive**
  ![11](./images/splunk/11.png)
3. Alerts dashboard is displayed, and it lists the alerts and related statistics from Cyble Vision platform
   ![12](./images/splunk/12.png)
4. Navigate to **Cyble IoC > IoC**
![13](./images/splunk/13.png)
5. IoCs dashboard is displayed, and it lists the IoCs and related statistics from Cyble Vision platform
![14](./images/splunk/14.png)


## View Logs

Follow the below steps to view and export logs related to Alerts and IoCs:

1. In Splunk Enterprise Platform, navigate to **Search & Reporting**
2. Search for the below query in the search bar for Cyble Alerts information
`index= "_internal""[CYBLE EVENTS]"`
![15](./images/splunk/15.png)
3. Search for the below query in the search bar for Cyble IoCs information
`index= "_internal""[CYBLE IOCS]"`
4. Export the results to Excel using **Save As** option
![16](./images/splunk/16.png)


## Troubleshooting

### Error in Log: Failed to decrypt the API key

**Error:**  Failed to decrypt the API key while executing IOC.py/Alerts.py for the Cybel Threat Intel application

**Cause:** Insufficient permissions to update the stored credentials

**Details:**  *“HTTP 403 Forbidden – the stored credential /nobody/CybleThreatIntel/passwords/credential::IOC could not be removed”*

**Resolution:**
1. Ensure that the Splunk user has the below permissions:
	a. admin_all_objects
	b. list_storage_passwords
2. If the issue persists, contact the Splunk admin or Splunk Support.


### Error: Unable to Fetch Data

**Resolution:**

1. [Export Logs](#View-Logs) and analyze it for any error. Share the files with CSM or Account Manager for any support if required
2. If no error is found in logs, reconfigure API key by following the [configuration](#Step2-Configuration) steps
	


## Upgrade


To upgrade the Cyble Threat Intel application, follow the below steps:

1. Download the latest version from Splunkbase
2. Open the Splunk Enterprise platform
3. Click **Manage**
![5](./images/splunk/5.png)
4. Click **Install app from file**
![6](./images/splunk/6.png)
5. Select the downloaded Cybel Threat Intel application file(*.spl*) and click **Upload**
6. Select **Upgrade app** to overwrite the existing application
![17](./images/splunk/17.png)
7. Restart Splunk when prompted

> **Note:** The error “credential manager issues” has been observed during upgrades. Check the logs for permission errors and contact Splunk support if required.


## FAQs
1. Do updates to the existing alerts in Cyble Vision reflect in Splunk?
No. Only the updates to newly ingested alerts are reflected in Splunk. Updates to previously existing alerts are not reflected.

2. How frequently are the alerts fetched from Cyble Vision?
Alerts are fetched incrementally based on the configured polling schedule. The polling schedule can be configured during Data Input Setup using the parameter **Interval**.

3. Can I apply custom filters to the incoming alerts?
No. Currently, only the predefined statuses are supported. Custom filtering is planned in the product roadmap.

4. What user permissions are required on Splunk to integrate Cyble Vision platform?
Ensure that the user role allows:
	a. Creation of modular inputs
	b. Edit/Write to the specified index

Typically, an admin or a user with similar access level can perform above actions.
