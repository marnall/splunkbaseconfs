# Cisco Cyber Vision App For Splunk
## Overview
* The App delivers a user experience designed to make Splunk immediately useful and relevant for typical tasks and roles. The Cisco Cyber Vision App for Splunk will provide the below functionalities:
  * Operational Summary Dashboard can be used to analyze the Operational Events, Component Summary, Top Protocols, and Top Talkers.
  * Security Insights Dashboard can be used to analyze the Security Events and vulnerabilities.
  * Syslog Overview Dashboard can be used to analyze the Syslog Security Events and Syslog Operational Events

* Author - Cisco Systems
* Version - 2.1.0


## Compatibility Matrix

|                           |                                                                            |
|---------------------------|----------------------------------------------------------------------------|
| Browser                   | Google Chrome, Mozilla Firefox                                             |
| OS                        | Linux, Windows                                                             |
| Splunk Enterprise Version | 9.2.x, 9.1.x, 9.3.x                                                        |
| Splunk Deployment         | Standalone, Distributed, Cluster                                           |
| API Version               | Events:1.0, Components:3.0, Activities:3.0, Flows:3.0, vulnerabilities:3.0 |
|                           |                                                                            |


## Release Notes

### Version 2.1.0
- Added filter on dashboards to visualize data based on Cybervision center.
- Updated the Icons.

### Version 2.0.0
- Added visualizations for Devices data.
- Updated macro definition to restrict the search to specific index.


### Version 1.1.0
- Minor enhancement in queries.


## Recommended System Configuration
- Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.


## Installation

Follow the below-listed steps to install an App from the bundle:

- Download the app package.
- From the UI navigate to  `Apps -> Manage Apps`.
- In the top right corner select `Install the app from file`.
- Select `Choose File` and select the App package.
- Select `Upload` and follow the prompts.
  OR
- Directly from the `Find More Apps` section provided in Splunk Home Dashboard.

## Configuration
For sending Syslog data to Splunk. Follow the below steps on your Cisco Cyber Vision instance:
- Go to `Admin > System` 
- Scroll down to the section `Syslog configuration`. Click on `Configure`
- Select `TCP` 
- Add the `hostname` and `port`,  Select `RFC 3164/CEF` in the format.
- Click on `Save Configuration`.

For configuring the data collection of Syslog follow the below-mentioned steps in Splunk.
- Go to `settings > data inputs > TCP`
- Click on `New Local TCP`
- Enter `Port`, Only accept connection from, and Source name override. Click `Next`
- From sourcetype dropdown select `cisco:cybervision:syslog`, app context as `TA Cisco Cyber Vision`, and select index. Click `Review`.
- Verify the details you have entered. Click on `Submit`.

For configuring the macro definition: 
- Navigate to Settings and then to Advanced search.
- Select Search macros.
- From the list of Apps, select Cisco Cyber Vision App For Splunk (cisco_cyber_vision_app_for_splunk)
- Set the list by Owner to Any and Created in App.
- Select `cisco_cybervision_index`. This opens the definition page of it.
- In Definition, change the index to the name of the index where Cisco Cyber Vision data is flowing in. For example, if the Cisco Cyber Vision data is flowing into the index named `test`, the definition would be `index=test`.
- Select Save to apply your changes.

## Dashboard Information
### Operational Summary Dashboard
#### Filters
| Name           | Description                                       |
|----------------|---------------------------------------------------|
| Time           | Splunk Time Range                                 |
| Presets        | Filtering out by searching text                   |
|                |                                                   |

#### Panels
This dashboard visualizing the `Cisco Cyber Vision Operations` category of Events, Components, Flows, and Activities events data.
- This dashboard contains the `Events Distribution By Severity Over Time` line-chart panel, `Events By Severity` pie-chart panel, `Components Details` panel, `Devices Details` panel, `Devices by DeviceType` pie-chart panel, `Top 10 Protocol` bar-chart panel, and `Top 10 Talker` bar-chart panel.
- `Components Details` panel can be filtered by the group.
- `Event By Severity` panel contains a drill-down and clicking on any slice will open two new panels named `Severity by Type` and `Event of Type`.
- `Severity by Type` contains drill-down and filters out the events in the `Event of Type` panel based on slice click.
- By clicking on any panel chart, you can get the raw events.
- `Devices Details` panel contains a drill-down and clicking on any row, you can get the raw event.
- `Devices by DeviceType` panel contains a drill-down and clicking on any slice, you can get the raw event.
### Security Insights Dashboard
#### Filters
| Name           | Description                                       |
|----------------|---------------------------------------------------|
| Time           | Splunk Time Range                                 |
| Presets        | Filtering out by searching text                   |
|                |                                                   |

#### Panels
- This dashboard is visualizing the `Security Events` category of events and vulnerabilities events. 
- This dashboard has the `Events Distribution By Severity Over Time` panel, `Events by Severity` panel, and `Top 10 Vulnerability` panel.
- `Event By Severity` panel contains a drill-down and clicking on any Slice will open two new panels named `Severity by Type` and `Event of Type`.
- `Severity by Type` contains drill-down and filters out the events in the `Event of Type` panel based on the clicked slice.
- By clicking on any panel chart, you can get the raw events.
### Syslog Overview Dashboard
This dashboard contains the syslog visualization.
#### Filters
| Name           | Description                                       |
|----------------|---------------------------------------------------|
| Time           | Splunk Time Range                                 |
| Presets        | Filtering out by searching text                   |
| Event Class ID | Event class id of syslog event attached in header |
|                |                                                   |
#### Panels
This Dashboard is divided into two parts. Security Syslog Events and Syslog Operational Events.

1. Security Syslog Events
    - This part contains two main panels named `Security Events Distribution By Severity Over Time` and `Security Events by Severity`.
    - By drilling-down on any pie-slice of the panel `Security Events by Severity` will open two new panels. One panel shows the further distribution by Event Class ID. Another panel named `All Security Events of <severity> Severity` shows the data in tabular form.
    - By drilling-down on the `Vulnerability Count` and `Vulnerable Component` fields, It will redirect you to another dashboard that contains the details of the assigned vulnerability of the selected component.
2. Operational Syslog Events
    - This part contains two panels named `Operational Events Distribution By Severity Over Time` and `Operational Events by Severity`.
    - By drilling-down on any pie-slice of the panel `Operational Events by Severity` will open two new panels. One panel shows the further distribution by Event Class ID. Another panel named `All Operational Events of <severity> Severity` shows the data in tabular form.


## Upgrade

### General Upgrade Steps
- Download the App package.
- Go to Apps > Manage Apps and click on the "Install app from file".
- Click on "Choose File" and select the Cisco Cyber Vision App for Splunk installation file.
- Check the Upgrade app checkbox and click on Upload.
- Restart the Splunk instance.

### From v2.0.0 to v2.1.0
- Follow the "General Upgrade Steps" section mentioned above.

### From v1.1.0 to v2.0.0
- Configure the macro definition mentioned in `Configuration` section.
- Follow the "General Upgrade Steps" section mentioned above.

### From v1.0.0 to v1.1.0
- No additional upgrade steps are required. follow the "General Upgrade Steps" section mentioned above.


## Troubleshooting

1. Panels are taking time to populate data: 
<br>-> User can configure specific index into the macro.
    - Select `Settings > Advanced Search > Search macros`.
    - Select the App named `Cisco Cybervision App for Splunk` from the dropdown.
    - Select the `cisco_cybervision_index` named macro
    - User can update the index in `Definition`.
    - Click on `Save` button to apply the changes.   

## Support Information
Email: cisco-cybervision-splunk@cisco.com

## Copyright Information
Copyright (c) 2013-2024 Cisco Systems, Inc
