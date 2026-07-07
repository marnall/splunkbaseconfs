# Skurio
The Skurio App for Splunk brings open, deep and DarkWeb data breach alert details into Splunk to help you improve incident response. 

Connection to the Skurio API enables the creation of Alerts on various types of data - emails, domains, IP addresses, card details, addresses etc. which are organized in folders. When confidential data matching these Alerts is leaked, marketed or sold on the Dark Web, Internet Relay Chat and bin sites, a result is posted via the API. The Skurio Splunk application regularly polls the API to pull in details of the breached data detected by Skurio

## Requirements
The Splunk integration is available to customers with the REST API add-on for their Skurio subscription. If you would like to upgrade your Skurio subscription to add API access, please contact [customersuccess@skurio.com](mailto:customersuccess%40skurio.com)

Access to Skurio requires registration on the [Skurio developer portal](https://api.skurio.com). Once registered, you can request access to the Skurio Alerts and Results API. You will be provided with two keys: an API key for your Skurio account, which must be requested from support@skurio.com, and an App key that is specific to your Splunk connection which can be requested via the api.skurio.com portal. Both keys are needed to activate the Splunk integration


## Setup
To install the Skurio App for Splunk:

1. Install the app by uploading a package or from Splunkbase
2. Restart Splunk if prompted
3. Optionally, create an index for the Skurio data. By default the Skurio dashboard displays data from indices that start with "skurio"
4. Navigate to Settings->Data inputs
6. Click "Add new" next to the Skurio entry in the Local inputs table to set up a new input
7. Enter your API and App keys. These will be stored securely by the app once submitted
8. Optionally enter searches to match folders and alerts in your Skurio account that you want to bring into Splunk. Leave these blank to bring in all results from Skurio. The searches are in Regex format.
9. Specify override_range if you want to pull historic data into Splunk. If left blank, only new results will be fetched
10. Check More settings
11. Optionally set the Interval, Source type and Host values. Note changing the Source type will prevent events from this input being mapped to the CIM model (see below)
12. Choose the destination index for Skurio results
13. Click Save 

The app will start to retrieve data as soon as it's configured

## Retrieving historical results
By default, Skurio data inputs bring in new results detected after the time they are configured. You can override this by going to the Skurio data input's settings and entering a date range in override_range. Once specified, clicking save will cause an immediate fetch of results from that range. Following that fetch, override_range is set back to None, and the input returns to pulling new data periodically.

The date range must be entered as "start end" with dates in yyyy-mm-dd format and single space between. 

e.g. for Sept 1 to Sept 30:  
`2019-09-01 2019-09-30`

Note that data is fetched up to, but not including the end date, so to fetch a full month of data, specify the first day of the next month as the end date.

## Skurio App Tabs
### Skurio Status
The default tab for the app shows four panes:

- Posts detected in the last 30 days: Daily count of the number of results from Skurio
- Post sources in the last 30 days: Breakdown of posts by source (e.g. dark web, irc, bins)
- Most focused posts in past 30 days: The posts that contained the highest percentage of matches to the search term. This indicates whether a post was entirely about your data, or just partially
- Top emails and passwords: The email accounts and redected passwords that have been detected most often since the beginning of the data in Splunk

### Search
This is just the regular search interface, allowing you to explore the Skurio data

### Datasets
Skurio defines a data model that can be useful for providing data to other components. This can be viewed here. If you need to edit this, we recommend you duplicate it and make changes in the copy

### Alerts
Add Skurio-specific alerts here

### Dashboards
Define Skurio-specific dashboards here

## CIM Compatibility
The Skurio App is compatible with CIM 4.x. 

The eventtype `Skurio_match` is tagged with `dlp` and `incident` to make it compatible with the `Data Loss Prevention - DLP Incidents` dataset using the following provided mapping:

| Field | Skurio Field | Skurio description | Data model description |
| --- | --- | --- | --- |
| action | "GenerateIncidentReport" | Constant value | The action taken by the DLP device. |
| app | "Skurio" | Constant value | The application involved in the event. |
| category | matchType | The type of data matched: `emails`, `ips`, `keywords`, `domains` | The category of the DLP event. |
| dest | - | - | The target of the DLP event. |
| dest_bunit | - | Automatically assigned by Splunk | The business unit of the DLP target. |
| dest_category | - | Automatically assigned by Splunk | The category of the DLP target. |
| dest_priority | - | Automatically assigned by Splunk | The priority of the DLP target. |
| dest_zone | - | - | The zone of the DLP target. |
| dlp_type | "breach-detection" | Constant value | The type of DLP system that generated the event. |
| dvc | folderName + "/" + alertName | The folder and name of the alert that triggered the result | The device that reported the DLP event. |
| dvc_bunit | - | Automatically assigned by Splunk | The business unit of the DLP target. |
| dvc_category | - | Automatically assigned by Splunk |  The category of the DLP device. |
| dvc_priority | - | Automatically assigned by Splunk | The priority of the DLP device. |
| dvc_zone | - | - | The zone of the DLP device. |
| object | matchedValue | The matched data detected by the alert | The name of the affected object.	|
| object_category | matchType | See `category` above | The category of the affected object.	|
| object_path | matchedValue | The matched data detected by the alert | The path of the affected object.	
| severity | sensitivityScore | A number between 0 and 1 reflecting the sensitivity of the information detected, where 1 is most sensitive. Not calculated for all results - "unknown" if not available | The severity of the DLP event. |
| signature | resultId | The ID of the result. Note that a single result may generate multiple events for each matched value | The name of the DLP event. |
| src	| postSourceUrl | The URL of the post where the match was detected, if available | The source of the DLP event. |	
| src_bunit | - | Automatically assigned by Splunk | The business unit of the DLP source. |
| src_category | - | Automatically assigned by Splunk | The category of the DLP source. |
| src_priority | - | Automatically assigned by Splunk | The priority of the DLP source. |
| src_user | author | The username of the person who posted the data, or "Unknown" | The source user of the DLP event. |
| src_user_bunit | - | Automatically assigned by Splunk | The business unit of the DLP source user. |
| src_user_category | - | Automatically assigned by Splunk | The category of the DLP source user. |
| src_user_priority | - | Automatically assigned by Splunk | The priority of the DLP source user. |
| src_zone | - | - | The zone of the DLP source. |
| tag | - | Automatically assigned by Splunk | This automatically generated field is used to access tags from within datamodels. |
| user | - | - | The target user of the DLP event. |
| user_bunit | - | Automatically assigned by Splunk | The business unit of the DLP user. |
| user_category | - | Automatically assigned by Splunk | The category of the DLP user. |
| user_priority | - | Automatically assigned by Splunk | The priority of the DLP user. |
| vendor_product | "Skurio:BreachAlert" | Constant value | The vendor and product name of the DLP system. |

## Troubleshooting
The Skurio App logs errors and informational messages to the _internal index. Use the following search to explore the logs from Skurio

```
index="_internal" execprocessor Skurio
```

## Support
If you have any problems, please contact [support@skurio.com](mailto:support%40skurio.com)