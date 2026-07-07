*****************************************
*
* App: Absolute Data and Device Security (DDS) App for Splunk
* Current Version: 1.0.3
* Last Modified: August 24, 2017
* Splunk Version: 6.4
* Author: Absolute Software Corporation
*
*****************************************

**** Overview ****
The Absolute Data & Device Security (DDS) App enables Splunk users to view the alert events logged in Absolute DDS in a format that enhances readability and analysis. After Splunk indexes the alert events, you can work with the event data using the set of predefined Splunk dashboards included with the app. You can also access the Absolute DDS Device Freeze feature directly from Splunk to freeze at-risk devices.

Before you can use the Absolute DDS App to view alert events, you need to install the Absolute SIEM Connector on a network computer running a supported version of the Windows operating system. For more information, see the Absolute SIEM Connector Install Guide, which is available on the Documentation page in the Absolute DDS console.

The Absolute DDS App is supported in Splunk Enterprise and Splunk Cloud.

**** Configuration Steps ****
Please refer to https://cc.absolute.com/Documents/GuidesAndTips/AbsoluteSIEMConnectorInstallGuide.en.pdf
for detailed configuration steps

**** Saved search shipped with the app ***
"AbsoluteSIEMConnector": This is the search string to find out events come from Absolute SIEM Connector

**** Selected event fields shipped with the app ***
The following fields are selected as default for events come from Absolute SIEM Connector:
"host"
"source"
"sourcetype"
"DDS_AlertCondition"
"DDS_AlertID"
"DDS_AlertName"
"DDS_AlertTime"
"DDS_Category"
"DDS_ComputerName"
"DDS_Identifier"
"DDS_SerialNumber"
"EventObject.DDS_AlertCondition"
"EventObject.DDS_AlertID"
"EventObject.DDS_AlertName"
"EventObject.DDS_AlertTime"
"EventObject.DDS_Category"
"EventObject.DDS_ComputerName"
"EventObject.DDS_Identifier"
"EventObject.DDS_SerialNumber"

**** Data models shipped with the app ***
The following data models are shipped with the app:
alert_events_by_alert_name_model.json: This data model is used for querying and summarizing Absolute DDS alert events based on Absolute DDS alert name.

alert_events_by_condition_name_model.json: This data model is used for querying and summarizing Absolute DDS alert events based on Absolute DDS alert condition message.

**** Alert action (workflow action) shipped with the app ***
There is one alert action shipped with the app.
Alert action id: "request_device_freeze"
Alert action label: "Request Device Freeze"
This alert action will navigate user to the Request Device Freeze page on the Absolute DDS Console (https://$DDS_Console$/dds5/administration/device-freeze?targetURL=%2FPages%2FAdministration%2FDeviceFreezeRequest.aspx%3FDDSIdentifier%3D$DDS_Identifier$%26EventObjectDDSIdentifier%3D$EventObject.DDS_Identifier$) to submit a device freeze request.
The URL parameters (DDS_Identifier and EventObject.DDS_Identifier) are the Absolute DDS identifier for each alert event. The $DDS_Console$ is cc.absolute.com or cc.us.absolute.com

**** Support contact information ***
Email: support@absolute.com
Support site/ticketing system: www.absolute.com/support
