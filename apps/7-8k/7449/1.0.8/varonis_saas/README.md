# Varonis SaaS Add-on for Splunk

Varonis SaaS is a Splunk application that provides insights from Varonis alerts data. 
It includes:
1. Modular input to collect data from the Varonis API
2. Dashboards to visualize and manage the alerts
3. Custom search command to query/manage the Varonis alerts data

## Installation

1. Download the "Varonis SaaS" app from [Splunkbase](https://splunkbase.splunk.com/apps?author=varonisapp).
2. In Splunk navigate to `Apps > Manage Apps > Install app from file`.
3. Upload the downloaded file and restart Splunk if prompted.
   
## Configuration

First you will need to create an API key from Varonis Web UI according to documentation: [API Key generation](https://help.varonis.com/s/document-item?bundleId=ami1661784208197&topicId=emp1703144742927.html&_LANG=enus).
Once the app is installed, you will need to provide the API key and Varonis Web UI Address in the app configuration:  
![setup.png](README%2Fsetup.png)\
Before completing the configuration, you can test the connection to the Varonis API by clicking on the `Test Connection` button.


### Modular Input Configuration

In navigation panel click on `Data Inputs`\
![Data Inputs](README%2Fmodular_input_1.png)\
(or in splunk navigate to `Settings > Data Inputs > Varonis SaaS`).  
Click on `New` to add a new input and provide the following details:
- Alert Retrieval Start Point: the past number of days from which to start retrieving alerts.
- Alert Retrieval Interval: Frequency in seconds for alert retrieval.
- Optionally: Add a filter to fetch alerts only for specific Threat Detection Policies, Alert Statuses or Alert Severities.

After modular input is configured, you can start the alerts will start pulling from Varonis API into `sourcetype=varonis:monitors`.

## Dashboards

The alerts data pulled into `sourcetype=varonis:monitors` can be viewed on Alerts Dashboards:
1. Alerts Dashboard: Provides an overview chart of alerts by severity, including the top number of alerts by user, asset, device and threat detection policy. ![Alerts Dashboard](README%2Falerts_dashboard_1.png)
2. Alerts Drill-Down Dashboard: Displays an overview chart of alerts for a specific user/asset/device/threat detection policy, including the list of alerts. ![Alert Details Dashboard](README%2Falerts_dashboard_2.png)


## Varonis Command

This Splunk custom search command allows users to interact directly with the Varonis API (not splunk indexed data) to fetch alerts, retrieve alerted events, update alert statuses, and obtain threat detection policies.

### Features

- **Get Alerts**: Retrieve specific alerts or sets of alerts based on criteria such as alert ID, severity, and status.
- **Update Alert**: Modify the status of an alert, add notes, or specify the close reason for an alert.
- **Get Alerted Events**: Fetch detailed event data for specific alerts.
- **Threat Model Retrieval**: Obtain a list of hreat detection policies from Varonis.

Examples can be found in the **Queries** section of the app.\
![Queries](README%2Fqueries_1.png)

### Alert Detailed View

This view allows to interact with the alert through Varonis API and perform actions like updating the alert status, adding notes, closing the alert, see the list of alerted events.
![Alert Detailed View](README%2Falert_detailed_view_1.png)
![Alert Detailed View](README%2Falert_detailed_view_2.png)

## Troubleshooting

To identify issues with the app, you can check the internal logs of the application.
It will display the logs for the modular input, custom search command, and other components of the app.
![Troubleshooting](README%2Ftroubleshooting_logs_1.png)


## Support

For information on how to contact support, refer to the Varonis support page at:
https://www.varonis.com/services/support

