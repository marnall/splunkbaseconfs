# ExtraHop Revealx App for Splunk
## Overview
* The ExtraHop RevealX App for Splunk receives ExtraHop RevealX NDR detection data from the Splunk event collector to build detection dashboards and to generate detection event alerts in Splunk based on correlation rules.

  RevealX NDR is the core cybersecurity module of the RevealX platform. It enables organizations to reduce risk and identify threats other tools like EDR and SIEM miss. By ingesting and analyzing network telemetry, RevealX NDR provides OSI Layer 2–Layer 7 visibility and real-time detection while providing streamlined investigation workflows for faster, more confident response across on-premises, remote, hybrid, and multicloud environments.

* Author - ExtraHop Networks
* Version - 1.0.2


## Compatibility Matrix

|                           |                                  |
|---------------------------|----------------------------------|
| Browser                   | Google Chrome, Mozilla Firefox   |
| OS                        | Linux, Windows                   |
| Splunk Enterprise Version | 9.4.x, 9.3.x, 9.2.x, 9.1.x       |
| Splunk Deployment         | Standalone, Distributed, Cluster |


## Release Notes

### Version 1.0.2
* Handled source and destination IP values from different fields.

### Version 1.0.1
* Handled source and destination IP values from different fields.

### Version 1.0.0
* Introduced the "ExtraHop Detections Overview" dashboard for the ExtraHop RevealX NDR detection data received through Splunk HEC.
* Implemented correlation rules to generate alerts in Splunk for low, medium, and high severity of ExtraHop detections.

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

## UPGRADE

### General Upgrade Steps

* Go to Apps > Manage Apps and click on the "Install app from file".
* Click on "Choose File" and select the 'ExtraHop-RevealX-App-for-Splunk' installation file.
* Check the Upgrade app checkbox and click on Upload.
* Restart the Splunk instance.

### From v1.0.1 to v1.0.2

* To upgrade ExtraHop RevealX App from v1.0.1 to v1.0.2 you need to follow general steps as mentioned above.

### From v1.0.0 to v1.0.1

* To upgrade ExtraHop RevealX App from v1.0.0 to v1.0.1 you need to follow general steps as mentioned above.

## Configure HEC token:
1. From the Splunk UI, navigate to the "Settings" > "Data Inputs" > "HTTP Event Collector".
2. Click on "New Token".
3. Enter `Name` for of the token. Click on "Next".
4. In Source Type section select `Select`. From `Select Source Type` dropdown select `extrahop-rx360-detection`.
5. Select allowed indexes to ingest data and set one index as default.
6. Click on "Review" > "Submit".

## Configure Macros:
* If the user using a main index or default index during data collection, then no need to perform this step. But if the user has given any custom index during data collection, then perform the following steps:
    
1. Go to "Settings" > "Advanced search" > "Search macros".
2. Select "ExtraHop Revealx App for Splunk" in "App" context dropdown.
3. Click on the `extrahop_index` macro from the shown table.
4. In the macro definition default value will be `index IN (main)`. Update the definition by replacing `main` with the index you used for data collection and save the configurations. For example: `index IN (extrahop)`.

## Dashboard Information
### ExtraHop Detections Overview
#### Filter
| Name           | Description                                       |
|----------------|---------------------------------------------------|
| Time           | Splunk Time Range                                 |
|                |                                                   |

#### Panels
- This dashboard contains the `Recommanded Detections` and `Total Detections` single-value panel, `Highest Risk Score` Radial Gauge panel, `Top Sources` and `Top Destinations` panel, `Sources and Destinations` sankey-diagram panel, `Top Detection Categories` pie-chart panel, `Top MITRE Techniques` `Recommended Detections` and `Detections Modified in Last 24 Hr` panel.
- By clicking on any panel chart, you can get the raw events.

## Correlation Rules

- This add-on includes three correlation rules that generate alerts based on risk scores. Each rule corresponds to a different severity level:
  1. Low Severity Alert - If risk score is in between 1 to 30
  2. Medium Severity Alert - If risk score is in between 31 to 79
  3. High Severity Alert - If risk score is in  between 80 to 99
- Execution Frequency: Every 15 minutes
- Scope: These rules check for ExtraHop detections generated within the last 15 minutes.

## Troubleshooting

1. Panels are taking time to populate data: 
<br>-> User can configure specific index into the macro.
    - Select `Settings > Advanced Search > Search macros`.
    - Select the App named `ExtraHop Revealx App for Splunk` from the dropdown.
    - Select the `extrahop_index` named macro
    - Make sure user has configured the same index on ExtraHop that mentioned in macro.
    - User can update the index in `Definition`.
    - Click on `Save` button to apply the changes.   

## Support Information
ExtraHop Support Link: https://customer.extrahop.com/s/

## Copyright Information
(c) 2025 ExtraHop Networks, Inc.