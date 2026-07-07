# DoppelVision

- [DoppelVision](#doppelvision)
  - [Introduction](#introduction)
  - [Sample Log Message](#sample-log-message)
  - [Query Sample](#query-sample)
  - [Collect Logs for DoppelVision](#collect-logs-for-doppelvision)
  - [Install the App and View the Dashboards](#install-the-app-and-view-the-dashboards)
    - [Requirement for app installation](#requirement-for-app-installation)
    - [Install](#install)
    - [Dashboards](#dashboards)
      - [Doppel Vision Dashboard](#doppel-vision-dashboard)
  - [Support](#support)

## Introduction
  Doppel Vision manages external threats at the speed of AI. Doppel technology identifies and takes down deep fakes, malicious impersonations, phishing, and disinformation campaigns targeting clients, and utilises proprietary AI and machine learning tools to automate threat detection and takedowns. These dynamic features enable Doppel Vision to scale with you as your partner in brand protection in an evolving threat landscape.
  | Dashboard | Description    |
  | :---:   | :---: |
  | [Doppel Dashboard] | The Doppel Dashboard provides a comprehensive overview of digital risk protection metrics and alerts, helping users monitor high-severity threats, analyse alerts by various categories, and gain actionable insights. |


## Sample Log Message


```text
{"event_type":"alert_updated","timestamp":" 2024-09-18T15:55:10.218017 ","updated_values":{"queue_state":"reported"},"alert":{"id":"MTN-2","doppel_link":"https://app.doppel.com/crypto/MTN-2","created_at":"2024-09-05T13:55:19.28432","entity":"phishing_wallet_v2","queue_state":"reported","entity_state":"resolved","severity":"medium","product":"domains","source":"user_report","notes":"No further action required","uploaded_by":"abhishek@doppel.com","tags":[]}}
```

## Query Sample

This is an example of a simple query that returns number alerts.

```text
 sourcetype="doppel_alerts" 
| dedup alert.alert_id | stats count
| count
```

## Collect Logs for DoppelVision

Doppel Vision App is going to collect data using [HTTP Event Collector.](https://docs.splunk.com/Documentation/SplunkCloud/latest/Data/UsetheHTTPEventCollector)

Configure the global settings of the app:
1. Login to Splunk instance -> settings -> Data Inputs -> HTTP Event Collector
   Lets configure the global settings by selecting "Global Settings"
   
2. Now you can search for the Global Settings on top right corner of the page. 
    1. Enable "All Tokens". 
    2. Default Source Type is "_json"
    3. Default index as main
    4. Enable SSL
    5. Now leave HTTP Port Number as 8088.

3. Now you can create a newToken by clicking on New Token on the top right corner of the page. 
    1. Click on New Token. 
    2. Give unique name to token as doppel_alerts.
    3. Click on Next.
    4. Add main in Select Allowed Tokens.
    5. Now click on preview.
    6. Next click on submit.
    7. You will get a new token.
    8. Copy the token and save it for further use.


## Install the App and View the Dashboards

### Requirement for app installation

Use the instruction from this [doc](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) to satify all the requirements for installing the Doppel Vision app.


### Install

Use the instruction from this [doc](https://docs.splunk.com/Documentation/AWSsecurity/1.1.0/InstallationConfiguration/InstallingtheapptoSplunkEnterprise) to install the Doppel Vision App.


### Dashboards

#### Doppel Vision Dashboard

Use this dashboard to monitor high-severity threats, analyse alerts by product, status, and threat type, and review overall alert volume.

Use this dashboard to:
1. Monitor high-severity threats and scan attacks.
2. Review alerts by status for troubleshooting configuration issues.
3. Understand how to fine-tune Doppel Vision based on alert metrics.                             


## Support

This application has been developed and is supported by Doppel. In case of technical questions, please contact Doppel support at support@doppel.com

