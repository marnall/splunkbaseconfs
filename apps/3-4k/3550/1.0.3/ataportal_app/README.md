# Advanced Threat Analytics Security Operations Add-on

## Introduction

This add-on allows Splunk to send data to the Advanced Threat Analytics (ATA) Platform as an alert action.

Documentation is also available [here](https://www.advancedthreatanalytics.com/atasplunkaddon.pdf).

## Pre-Installation

Before performing Splunk integration setup procedures, ensure that you have the integration information **from ATA** for your specific user:
* Unique organization ID
* Authorization token

## Installation

1. Download the Advanced Threat Analytics Security Operations application from Splunkbase.
2. In Splunk, click either the **Apps** gear icon, or the **Manage Apps** shortcut menu item.
3. Click **Install app from file**.
4. Click **Choose File**, select *ataportal_app.spl*, and click **Upload**.
5. Click the **Set up now** button to configure the app for your organization.  You MUST be a customer of ATA or a MSSP that leverages the ATA Platform.
6. Provide the Advanced Threat Analytics Server URL, Authorization Token, and your Customer ID (unique Organization ID).

Once saved, the Advanced Threat Analytics Security Operations add-on for Splunk is installed and ready to be set up.

## Usage

Within any alert, you can specify security events to be sent to the ATA Platform when the alert is fired.
Open or create your alert, select **Add Actions**, select the **ATA IR Portal Alert Action** dropdown, and fill in the alert dialog box.

After adding the Action, you will be able to add additional fields that can be customized on a per-Alert basis.  These fields are *optional* and include the following. Any of these fields that are sent, with the exception of *Title* and *Event Grouping* can be used for searching and filtering on the ATA IR Portal.
*	*Title* – override the default Incident Title that’s created by ATA IR Portal
*	*Event Grouping* – how the ATA Portal will group events.  This should be one of the fields present in the log event.  Leave blank to use ATA Portal default (hostname or IP address).
*	*Category* – category of the Security Event sent
*	*Priority* – Priority of the Security Event sent
*	*Type* – Type of the Security Event being sent

## Contact

For app support please contact [support@advancedthreatanalytics.com](mailto:support@advancedthreatanalytics.com)

## License
The ATA Security Operations Add-on is licensed under the Splunk End User License Agreement for Third Party Content. More details are available [here](https://d38o4gzaohghws.cloudfront.net/static/misc/eula.html).
