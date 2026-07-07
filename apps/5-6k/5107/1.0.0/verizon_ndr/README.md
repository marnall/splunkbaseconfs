## **Table of Contents**

### **OVERVIEW**

- About the Verizon Network Detection and Response App for Splunk
- Release notes
- Support and resources

### **INSTALLATION**

- Hardware and software requirements
- Installation steps

### **USER GUIDE**

- Key concepts

### **OVERVIEW**

#### **About the Verizon Network Detection and Response App for Splunk**

| Author | Verizon |
| --- | --- |
| App Version | 1.0.0 |
| Vendor Products | Verizon NDR Syslog Emitter v2.61 and above |
| Has index-time operations | False |
| Create an index | False |
| Implements summarization | False |

The Verizon Network Detection and Response App for Splunk is a solution that enables the viewing and organizing of Verizon NDR technical anomaly events and observations in Splunk. It also allows the ability to pivot into the Verizon NDR Visualizer from within your Splunk deployment to enhance your ability to detect and respond to attacks and/or network anomalies.

##### **Scripts and binaries**

N/A

#### **Release notes**

##### **About this release**

Version 1.0.0 of the Verizon Network Detection and Response App for Splunk is compatible with:

| Splunk Enterprises versions: | 6.x and above |
| --- | --- |
| CIM: | N/A |
| Platforms: | Platform Independent |
| Vendor Products: | Verizon NDR Syslog Emitter v2.61 and above |
| Lookup file changes: | None |

##### **New features**

Verizon Network Detection and Response App for Splunk includes the following new features:

- Added the following dashboards: Investigative Dashboard, Situational Dashboard, Search

## **INSTALLATION AND CONFIGURATION**

### **Hardware and software requirements**

#### **Hardware requirements**

Verizon Network Detection and Response App for Splunk supports the following server platforms in the versions supported by Splunk Enterprises.

- Platform Independent

#### **Software requirements**

To function properly, Verizon Network Detection and Response App for Splunk requires the following software:

- Verizon Network Detection and Response AddOn for Splunk
- Verizon NDR Syslog Emitter v2.61 and above

#### **Splunk Enterprise system requirements**

This app runs on Splunk Enterprises. All of the Splunk Enterprises system requirements apply. [http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements)

#### **Installation steps**

To install and configure this app on your supported platform, follow these steps:

##### Web UI #####

1. Click on the gear next to Apps
2. Click on Install App from File
3. Chose downloaded file and click upload
4. Restart Splunk

##### Configuration Files #####

1. Untar downloaded file
2. Copy or move verizon_ndr folder to SPLUNKBASE/etc/apps
3. Restart Splunk

##### Deploy to single server instance

Install using one of the methods above.

##### Deploy to distributed deployment

**Install to search head**

Install using one of the methods above. No other instance in a distributed deployment needed to have this app installed on.

#### **Configuration**

**Macros** : Reusable chunks of Search Processing Language (SPL) that you can insert into other searches.

1. Update the definition of the **pw\_baseurl** macro with your Verizon NDR domain in order to be redirected to the proper site when drilling down from the Situational Details dashboard.

**Workflows** : A highly configurable knowledge object that enables a variety of interactions between Splunk fields in events and other web resources.

1. Default base URL: visualizer.protectwise.com/
2. If your base URL has been changed, update the following workflow actions:
    1. splunk\_search\_src\_ip
    2. splunk\_search\_dest\_ip
    3. pw\_search\_killbox\_ob\_id
    4. pw\_search\_killbox\_ob\_dest\_ip
    5. pw\_search\_killbox\_ob\_src\_ip
    6. pw\_search\_explorer\_ob\_src\_ip
    7. pw\_search\_explorer\_ob\_dest\_ip

## **USER GUIDE**

### **Key concepts for Verizon Network Detection and Response App for Splunk**

The Verizon Network Detection and Response App for Splunk uses the power of Verizon NDR and combines it with the search power of Splunk. Investigations of Events and Observations can take advantage of Splunk&#39;s business intelligence interface and search system UI that allows users to pivot into the Verizon NDR Visualizer.

### **Investigative Dashboard**

Investigation focuses on Events and their associated Observations. It features in-page drilldowns that provide the user the details of each observations that attributed to an event. Users can search other data sources in Splunk for specific destination or source IPs by utilizing the workflow actions associated with the Observation Details panel.

### **Situational Details Dashboard**

This dashboard focuses on all Verizon NDR observations. Provides an overview of the observation Killchain Stages and displays the trend over time. Users can see details about each observations filtering by type, host, or category. Clicking on an IP in the Observation Details panel directs users to the Verizon NDR Visualizer to further their investigation.

**Transfom/Alias**

Field aliases that normalize the Verizon NDR data to fit the CIM can be found in the props.conf file in the app.
