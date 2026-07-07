# SysCloud Add-on for Splunk

## Introduction
The SysCloud Add-on for Splunk enables the collection of events from SysCloud directly within Splunk. These events, which are logs or records, are pushed to Splunk for enhanced analysis and visualization.

## Prerequisites
To use this add-on, you will need the following:
- **Client Credentials**: Specifically, a `ClientID` and `ClientSecret`.
  - Visit the [SysCloud Developer Portal](https://developers.syscloud.com) for detailed instructions on how to set up an API client and obtain these credentials.

## Installation
To install the SysCloud Add-on for Splunk, you can follow these steps:

1. **Install via Splunkbase**:
   - Navigate to the **"Find More Apps"** section on the Splunk homepage.
   - Search for **"SysCloud Add-on for Splunk"** and follow the installation instructions.

2. **Manual Installation**:
   - Download the SysCloud Add-on package.
   - From the Splunk homepage, go to **Apps > Manage Apps**.
   - In the top-right corner, select **Install app from file**.
   - Choose the downloaded file and upload it to complete the installation.

## Configuration
After installing the add-on, follow these steps to set it up:

1. **Access the Configuration Settings**:
   - Go to the **SysCloud Add-On for Splunk** app.
   - Click on the **Configuration** tab and select **Add-on settings**.

2. **Add Client Credentials**:
   - Enter your `ClientID` and `ClientSecret` obtained from SysCloud.
   
3. **Create New Inputs**:
   - Navigate to the **Input** page within the add-on.
   - Click **Create New Input** and select the desired input type from the dropdown. This will open a pop-up window.
   - In the pop-up, provide the following information:
     - **Name**: A unique name for the input.
     - **Interval**: The frequency at which data should be populated (refer to the documentation for recommended intervals).
     - **Index**: Specify the index in which the data should be stored.
     - **Cloud Selection**: Choose the cloud platforms for which data needs to be populated.

Once configured, the SysCloud Add-on for Splunk will start collecting and displaying SysCloud events for analysis.


# Binary File Declaration

The following binary files are included in this app:

- `bin/ta_syscloud/aob_py3/yaml/_yaml.cpython-37m-x86_64-linux-gnu.so`: This is a compiled shared object and precompiled binary file and not require source code
