Verizon Network Detection and Response Add-On for Splunk
=============================

## **Table of Contents**

### **OVERVIEW**

- About the Verizon NDR addon for Splunk
- Release notes
- Support and resources

### **INSTALLATION**

- Hardware and software requirements
- Installation steps

### **USER GUIDE**

- Key concepts

### **OVERVIEW**

#### **About the Verizon NDR addon for Splunk**

| Author | Verizon Network Detection and Response |
| --- | --- |
| App Version | 1.1.0 |
| Vendor Products | Verizon Network Detection and Response Syslog Emitter v2.61 and above |
| Has index-time operations | True |
| Create an index | True |
| Implements summarization | False |

TA-verizon_ndr is a solution that enables the viewing and organizing of Verizon Network Detection and Response technical anomaly events and observations in Splunk. It also allows the ability to pivot into the Verizon Network Detection and Response Visualizer from within your Splunk deployment to enhance your ability to detect and respond to attacks and/or network anomalies.

##### **Scripts and binaries**

N/A

#### **Release notes**

##### **About this release**

Version 1.1.0 of Verizon NDR addon for Splunk is compatible with:

| **Splunk Enterprises versions:** | **6.x, 7.x, 8.x and above** |
| --- | --- |
| CIM: | 4.x |
| Platforms: | Platform Independent |
| Vendor Products: | Verizon Network Detection and Response Syslog Emitter v2.61 and above |
| Lookup file changes: | None |

## **INSTALLATION AND CONFIGURATION**

### **Hardware and software requirements**

#### **Hardware requirements**

TA-verizon_ndr supports the following server platforms in the versions supported by Splunk Enterprises.

- Platform Independent

#### **Software requirements**

To function properly, TA-verizon_ndr requires the following software:

- Verizon Network Detection and Response Syslog Emitter v2.61 and above

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
2. Copy or move TA-verizon_ndr folder to $SPLUNKHOME/etc/apps directory
3. Restart Splunk


##### Deploy to single server instance

Install TA-verizon_ndr using one of the methods described above.

##### Deploy to distributed deployment

**Install to search head**

TA-verizon_ndr doesn't need to be installed onto search heads.

**Install to indexers**

Install TA-verizon_ndr using one of the methods described above.

**Install to forwarders**

Install TA-verizon_ndr using one of the methods described above.

#### **Configuration**

**TA-verizon_ndr:** This TA contains a template input.conf.template that can be used to create an inputs.conf.  The indexes.conf file has been removed from this version.

Has index-time properties: True

Creates custom index: False

**Forwarders:**
1. Place TA-verizon_ndr in the $SPLUNK\_HOME/etc/apps dir of your forwarder(s).
2. For the inputs.conf for the forwarders: The default location for the Verizon Network Detection and Response Emitter logs is as follows: /tmp/spl. If you have updated this location, update the inputs.conf.template file with the path for each monitor stanza. (Be sure to include the preceeding forward slash so there will be a total of three forward slashes after &#39;monitor:&#39;)
3. Include an index=<VALUE> attribute for the index you plan on ingesting Verizon Network Detection and Response data into.  This index must exist on your indexer(s) before enabling your inputs. If an index value is not added per monitoring stanza, the data will default to your main index.

Example:
[monitor://&lt;custom\_path&gt;/events.out]

index = verizon_ndr

sourcetype = verizon_ndr\_emitter

**Indexers:**
1. The recommended index for use with The Verizon Network Detection and Response App for Splunk is 'verizon_ndr'.

## **USER GUIDE**

### **Key concepts for TA-verizon_ndr**

The TA-verizon_ndr addon uses the power of Verizon Network Detection and Response and combines it with the search power of Splunk. Investigations of Events and Observations can take advantage of Splunk&#39;s business intelligence interface and search system UI that allows users to pivot into the Verizon Network Detection and Response Visualizer.

**Transfom/Alias**

Field aliases that normalize the Verizon Network Detection and Response data to fit the CIM can be found in the props.conf file in the app.
