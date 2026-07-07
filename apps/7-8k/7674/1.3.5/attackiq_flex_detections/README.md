# Introduction

AttackIQ Flex provides a secure and straightforward method for evaluating your security measures through simulated attacks. By running pre-configured tests and uploading the output, you can obtain results in minutes. The **AttackIQ Flex Detections App** enables you to validate both preventions and detections for every test conducted.

---

## Version Support

The **AttackIQ Flex Detections App** supports the following Splunk platform versions:

- **Splunk Enterprise:** 9.x, 10.x
- **Splunk Cloud Platform:** Compatible with the latest Splunk Cloud Platform version

**Note:** Older versions of Splunk Enterprise (prior to 8.2.x) have not been tested and are not officially supported. They may work, but functionality is not guaranteed.

---

## System Requirements and Prerequisites

To successfully use this app:

- Your Splunk platform instance must ingest **security events** to enable correlation and validate detections based on AttackIQ Indicators of Compromise (IOCs).
- Security events must include accurate timestamps reflecting the time when suspicious or malicious behaviors were detected by security controls.
- The `aiq_flex` index must be created as part of the app setup process. Follow the instructions provided within the app to ensure the index is properly configured.

### Expected Knowledge

Users of this app should:

- To use this app, you should have access to **AttackIQ Flex** and the AttackIQ Flex credits to run the test packages that meet your testing needs.
- Be familiar with AttackIQ Flex test packages, SIEM event correlation, and Indicators of Compromise (IOCs).

---

## Installation

### **Important Requirement**
The `aiq_flex` index must be created manually in your Splunk platform environment before using the **AttackIQ Flex Detections App**. This index is required for storing and visualizing data correlated with security events. Instructions for creating this index are provided within the app. Please refer to the app's setup guide to complete the configuration.


### For Splunk Enterprise
The **AttackIQ Flex Detections App** can be deployed in the following scenarios:

- **Distributed Environment:** Deploy the app on a **Search Head** to visualize and correlate data from your Indexers.
- **All-in-One Instance:** For smaller environments, deploy the app directly on an all-in-one Splunk platform instance, which serves as both the Search Head and Indexer.

### For Splunk Cloud Platform
The **AttackIQ Flex Detections App** is compatible with Splunk Cloud Platform and should be deployed as a self-service or managed app depending on your Splunk Cloud Platform subscription type. Ensure that the necessary permissions are available to install apps in your Splunk Cloud Platform environment.

The app is designed to visualize data correlated with security events ingested into your Splunk platform environment.

---

## Configuration

The app is pre-configured to correlate events from any product sending data to the Splunk platform. To enhance efficiency, navigate to the **Settings** tab and use the **Advanced Fine-Tuning** options. These allow you to select specific products sending data to your Splunk platform environment, focusing the app's correlation processes on the products most relevant to you.

---

## Running of the app

### Automatic Data Transfer

Follow these steps for automated integration between AttackIQ Flex and the Splunk platform:

1. **Setup in the Splunk platform:**
   - Create an HTTP Event Collector (HEC) token to enable automatic data transfer.

2. **Configure in Flex:**
   - Go to **Configuration > Detections** in AttackIQ Flex, enter the HEC token details, and save.

3. **Run the Test:**
   - Execute the test on an endpoint using the agent of the security product you want to validate. The agent sends detected behavior events to the Splunk platform.

4. **Automatic Transfer:**
   - Upon test completion, AttackIQ Flex sends prevention and detection data directly to the Splunk platform.

5. **Analyze Results:**
   - Use the AttackIQ Flex app in the Splunk platform to automatically correlate the data. View results in the **Overview**, **Flex Packages**, **Test Points**, and **Execution** tabs to assess your security product’s effectiveness.

### Manual Data Transfer

For manual validation, follow these steps:

1. **Download the Test Package:**
   - Choose and download a test package from AttackIQ Flex.

2. **Run the Test:**
   - Execute the test on an endpoint using the agent of the security product you want to validate. The agent sends event data to the Splunk platform.

3. **Upload to Flex:**
   - Upload the test output file to the **Analyze** tab in AttackIQ Flex. Flex will generate a `.zip` file containing prevention and IOC data.

4. **Upload to the Splunk platform:**
   - Download the `.zip` file from Flex and upload it via the **Data** tab in the AttackIQ Flex app.

5. **Analyze Results:**
   - The app will correlate the uploaded data. Review prevention and detection insights in the **Overview**, **Flex Packages**, **Test Points**, and **Execution** tabs.

---

## Troubleshooting

### Potential Issues and Resolutions

#### No data is visible in the dashboards:

- Ensure the appropriate **Time Range** is selected.
- Confirm that AttackIQ detections have been uploaded manually or via the HTTP Event Collector within the selected time range.
- Verify that the user account has the necessary permissions to view the data and dashboards.

#### No detections are present:

- Ensure that security events were generated after executing the package by searching for your security vendor's events within the relevant time window.
- Understand the AttackIQ IOCs that are correlated by searching in the Splunk platform with:
  ```spl
  sourcetype=aiq:flex:iocs "hostname_where_package_was_executed"
  ```

### Contact us
For application support, please contact us at flex-support@attackiq.com

---

## Reference Material

### Saved Searches

This app includes **9 saved searches** designed to identify **Indicators of Compromise (IOCs)** and correlate them with events in your Splunk platform environment to find relevant detections.

- **1 Generic Search:** Enabled by default, it identifies IOCs and correlates them with events across all sourcetypes.
- **8 Specific Searches:** Disabled by default, these focus on identifying IOCs and correlating them with events for specific sourcetypes. These searches can be enabled as needed in the app's **Settings** section in the UI.

### `upload_csv.py`

The **`upload_csv.py` script** is located in the app's `bin` folder and handles manual data uploads. It processes IOC and prevention data from CSV files and ingests them into the appropriate sourcetypes (`aiq:flex:iocs` and `aiq:flex:preventions`) for use in the app's saved searches and dashboards.

#### **Goal:**
- To provide a straightforward way to manually upload IOC and prevention data when automation (e.g., HTTP Event Collector) is not available.

#### **Benefit:**
- Enables users to manually test and validate detections, ensuring the app remains functional even in environments without automated data ingestion pipelines.

### Sourcetypes Used in the App

The app uses three primary sourcetypes:

1. **`aiq:flex:iocs`**
   - Stores IOCs data generated by AttackIQ package executions.
   - Used by the saved searches for correlating IOCs with events in your Splunk platform environment.

2. **`aiq:flex:preventions`**
   - Stores prevention status data generated by AttackIQ package executions.
   - Helps track the effectiveness of security controls in preventing malicious behavior.

3. **`aiq:flex:detections`**
   - Stores detection results generated by the app’s saved searches when an IOC matches with events in your Splunk platform environment.
   - Powers dashboards and reports, providing actionable insights into threat detection.

