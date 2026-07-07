## Splunk Alert Action for SAP® Enterprise Threat Detection Documentation

#### Table of Contents
1. App Description
2. Installation
3. Configuration
4. Alert Payload
6. Troubleshooting

#### App Description
Splunk Alert Action for SAP® Enterprise Threat Detection is a Splunk App that provides a Custom Alert Action for sending alerts from Splunk to an SAP® Enterprise Threat Detection deployment.  A Setup UI is provided to configure the remote SAP® Enterprise Threat Detection server and Console Dashboard for debugging.

#### Installation
* If you have internet access from your Splunk server, download and install the app by clicking “Browse More Apps” from the Manage Apps page in the Splunk platform
* Otherwise, download the app from Splunkbase and install it using the Manage Apps page in the Splunk platform.

#### Configuration
* The SAP® Enterprise Threat Detection Setup user interface can be found in the Splunk Alert Action for SAP® Enterprise Threat Detection by clicking on the Configure navigation bar item.
* Configure the Splunk Alert Action by providing the Base URL (Service Management Scheme/Host/Port), Username, and Password.  Note: Passwords are stored in encrypted format on Splunk using the storage service.
* Specifications for configuration may be found in the app/sap_enterprise_threat_detection/README/alert-actions.conf.spec file and how Splunk Custom Alert Actions work at https://docs.splunk.com/Documentation/Splunk/8.0.3/AdvancedDev/CustomAlertScript

#### Alert Payload
The alert payload specification sent from Splunk can be found here: $SPLUNK_HOME/app/sap_enterprise_threat_detection/ALERT_PAYLOAD.spec

#### Troubleshooting
Splunk logs all SAP® Enterprise Threat Detection alert action attempts.  Within Splunk Alert Action for SAP® Enterprise Threat Detection, click on the “Console” link within the navigation.  This will give you a summary of all transaction including errors over time.
