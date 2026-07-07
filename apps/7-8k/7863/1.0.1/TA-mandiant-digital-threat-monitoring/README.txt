# Mandiant Digital Threat Monitoring Add-on for Splunk

## Overview

The Mandiant Digital Threat Monitoring Add-on for Splunk provides a seamless integration to ingest and visualize alerts from the Mandiant Digital Threat Monitoring service. This add-on allows users to configure multiple data inputs, to periodically fetch alerts. A dedicated dashboard offers a comprehensive overview of the ingested alerts, enabling security analysts to quickly identify and act on potential threats.

## Compatibility Matrix

| Splunk Version | OS                |
| :------------- | :---------------- |
| 9.2, 9.3, 9,4  | Linux, Windows    |

## Installation

1.  Download the Mandiant Digital Threat Monitoring Add-on for Splunk package.
2.  Navigate to **Apps > Manage Apps** in your Splunk instance.
3.  Click on **Install app from file**.
4.  Select the downloaded package and click **Upload**.
5.  Restart Splunk for the changes to take effect.

## Configuration

Global configurations for the add-on can be accessed by navigating to the add-on's configuration page.

### Proxy

If your Splunk instance requires a proxy to connect to external services, you can configure the proxy settings in this section. You will need to provide the proxy host, port, and credentials if required.

### Logging

Configure the logging level for the add-on to control the amount of information that is written to the logs. Available levels are typically `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. The default is usually `INFO`.

### Settings

This section allows you to configure the global settings for the add-on's.

* **Index**: Specify the Splunk index where the dashboard will read the alert data from. The default value is `dtm`.
* **Index sensitive information**: By default, sensitive fields such as `doc.payment_card`, `doc.service_account`, and `topics` are not ingested. Check this box to enable the ingestion of this sensitive information.

## Inputs

To start ingesting alerts, you need to configure one or more inputs. From the add-on's "Inputs" page, click on **Create New Input** to open the "Add DTM Alerts" modal.

* **Name**: A unique name for this data input. This is used to identify the input in Splunk.
* **Interval**: The time interval in seconds for fetching new alerts from the Mandiant API.
* **Index**: The Splunk index where the alerts from this input will be stored. The default is `default`.
* **Global Account**: Select the Mandiant API account to use for this input.
* **Minimum M-Score**: The minimum M-Score value for an alert to be ingested. The M-Score is Mandiant's proprietary risk score.
* **Alert Status**: Filter alerts by their status. You can select one or more statuses to ingest. The "All" option ingests alerts regardless of their status.
* **Alert Types**: Filter alerts by their type. You can select one or more alert types to ingest. The "All" option ingests all types of alerts.

## Dashboard

The add-on includes a pre-built dashboard to visualize and analyze the ingested alerts.

### Overview

The dashboard provides a high-level overview of the alerts over the last 7 days. It includes two main panels:

* **Alerts by Severity**: A line chart that displays the trend of alerts over time, categorized by severity (e.g., Low, High). This helps in identifying spikes in alert activity.
* **Alerts by Type**: A bar chart that shows the distribution of alerts based on their type, providing a quick look at the most common types of threats detected.

### Alerts Table

Below the overview charts, there is a detailed table of the latest alerts. The table provides the following information for each alert:

* **Updated At**: The timestamp of when the alert was last updated.
* **Title**: A descriptive title of the alert.
* **Type**: The type of the alert (e.g., `Compromised Credentials`, `Leaked Web Service Credentials`).
* **Monitor**: The specific monitor in Mandiant that generated the alert (e.g., `Compromised Credentials`, `Deep & Dark Web`).
* **Severity**: The severity level of the alert (e.g., `Low`, `High`).
* **Confidence**: A numerical score indicating the confidence level of the alert.
* **Gemini Summary**: A brief summary of the alert.
* **Alert Detail**: A **View** button to navigate to a detailed view of the alert in Mandiant platform.

### Functionality and Filters

* **Time Range Picker**: The dashboard allows you to select the time range for the data being displayed. The default is the "Last 7 days".
* **Filters**: You can filter the alerts displayed in the table using the following dropdown menus:
    * **Filter by Severity**: Filter alerts by their severity level.
    * **Filter by Type**: Filter alerts by their type.
    * **Filter by Monitor**: Filter alerts by the monitor that generated them.
* **Pagination**: The alerts table is paginated, allowing you to navigate through a large number of alerts.

## Support

For any questions, issues, or feature requests, please contact our support team at: contact@virustotal.com

## F.A.Q.

**Q: Where can I find my Mandiant API credentials to configure a Global Account?**
**A:** You can find your Mandiant API credentials in your Mandiant Digital Threat Monitoring portal under the API settings section.

**Q: What is the M-Score?**
**A:** The M-Score is Mandiant's proprietary risk score that helps to prioritize alerts. A higher score indicates a higher risk.

**Q: Can I create multiple inputs with different configurations?**
**A:** Yes, you can create as many inputs as you need, each with its own set of filters for M-Score, Alert Status, and Alert Types, and specify a different index for each if required.

**Q: Why are some fields like `doc.payment_card` not appearing in my events?**
**A:** By default, sensitive information is not indexed to protect privacy and reduce noise. You can enable the ingestion of sensitive fields in the "Settings" under the add-on's configuration page.

**Q: How can I customize the dashboard?**
**A:** You can clone the provided dashboard and then edit the cloned version to add, remove, or modify the panels and visualizations to fit your specific needs.
# Binary File Declaration
/Users/nicolasromero/Documents/Splunk 9.4.1/splunk/var/data/tabuilder/package/TA-mandiant-digital-threat-monitoring/bin/ta_mandiant_digital_threat_monitoring/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
/Users/nicolasromero/Documents/Splunk 9.4.1/splunk/var/data/tabuilder/package/TA-mandiant-digital-threat-monitoring/bin/ta_mandiant_digital_threat_monitoring/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
