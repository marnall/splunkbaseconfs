# Trend Micro DDI Splunk Add-On

![Trend Micro DDI Add-On Logo](static/logo/logo.png)

## **Overview**

The **Trend Micro DDI Splunk Add-On** is designed to enhance your Splunk deployment by providing robust parsing capabilities for **Trend Micro Deep Discovery Inspector (DDI)** logs. This add-on focuses solely on parsing already ingested logs, ensuring that your security data is accurately extracted, categorized, and ready for analysis. By aligning with Splunk's Common Information Model (CIM), it facilitates seamless integration with other Splunk apps and dashboards, enabling efficient security monitoring and incident response.

**Purpose of the Add-On:**

After extensive research into existing Splunk add-ons for parsing Trend Micro DDI logs, no suitable solutions were found that met the specific needs for comprehensive parsing and log categorization. Consequently, this add-on was developed to fill that gap, providing a tailored solution for organizations leveraging Trend Micro DDI with Splunk.

## **Purpose and Functionality**

- **Purpose**:
  - To provide a streamlined solution for parsing and categorizing Trend Micro DDI logs within Splunk.
  - To enhance the visibility and analysis of security events without managing data ingestion processes.
  - To offer a foundation for future enhancements, including dashboard integrations and advanced analytics.

- **How It Works**:
  - **Log Parsing**: Extracts critical fields from Trend Micro DDI logs using guidelines from the [Trend Micro DDI Documentation](https://docs.trendmicro.com/o-help/manual/ad50c2e4-dd3a-40bf-a98e-f6b28951fedc/ddi_6.7.SP1_sg.pdf), enabling detailed analysis and reporting.
  - **Event Categorization**: Defines specific event types based on log characteristics to streamline searches and dashboards.
  - **Tagging**: Assigns relevant tags to events, facilitating alignment with Splunk's CIM and enhancing search efficiency.
  - **CIM Compliance**: Ensures that parsed fields and tags adhere to Splunk's CIM standards, promoting consistency across your Splunk environment.
  - **Future Enhancements**: Plans to develop and integrate dashboards for visualizing parsed data and enhancing user interaction.

**Note**: This add-on is a work in progress. While it provides essential parsing and categorization functionalities, it is not yet perfect. Ongoing development is planned to refine existing features and introduce new capabilities, such as dedicated dashboards for comprehensive data visualization.

## **Prerequisites**

Before installing the **Trend Micro DDI Splunk Add-On**, ensure that the following prerequisites are met:

- **Splunk Enterprise**: Version 8.0 or higher.
- **Python**: Python 3.6 or higher installed on the Splunk server (if required by custom scripts).
- **Trend Micro Deep Discovery Inspector (DDI)**:
  - Properly configured to send logs to Splunk using appropriate data inputs (e.g., syslog, heavy forwarder).
  - Logs must be assigned the correct sourcetypes as defined by the add-on:
    - `trendmicro:ddi`
    - **Administrative Permissions**: Required to install apps and configure data inputs in Splunk.

## **Developed By**

The **Trend Micro DDI Splunk Add-On** was developed by:

- **Ayed Abukhass**

## **Support**

For support and assistance with the **Trend Micro DDI Splunk Add-On**, please contact:

- **Support Email**: [aabukhass@outlook.com](mailto:aabukhass@outlook.com)

**Support Hours**: Sunday to Thursday, 9:00 AM to 5:00 PM UTC+3

## **Installation**

### **Installing in Distributed Environments**

- install the add-on on Heavy Forwarders, Search Heads, and Indexers in a distributed Splunk deployment.

### **1. Download the Add-On**

- Obtain the latest version of the **Trend Micro DDI Splunk Add-On** from [Splunkbase](https://splunkbase.splunk.com/) or your internal repository.

### **2. Install via Splunk Web**

1. **Navigate to Splunk Web**:
   - Open your Splunk instance in a web browser.
   - Go to **Apps > Manage Apps > Install app from file**.

2. **Upload the Add-On Package**:
   - Click **Choose File** and select the downloaded `.tar.gz` file.
   - Click **Upload**.

3. **Restart Splunk**:
   - After installation, Splunk will prompt you to restart. Click **Restart Splunk** to apply the changes.

### **3. Install via CLI**

1. **Copy the Add-On Package**:
   - Transfer the `.tar.gz` file to your Splunk server.

2. **Run the Installation Command**:
   ```bash
   $SPLUNK_HOME/bin/splunk install app /path/to/TrendMicro_DDI_Splunk_AddOn.tar.gz -auth admin:changeme
