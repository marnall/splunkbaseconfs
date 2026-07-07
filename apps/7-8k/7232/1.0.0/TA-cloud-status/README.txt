

# Cloud Status Add-on

## Overview

The Cloud Status Add-on for Splunk is designed to collect real-time status updates and health information from various cloud service providers and monitoring tools via RSS feeds. It enables users to monitor the operational status of cloud platforms, log monitoring & APM services, email & other apps, ITSM tools, and audio/video conferencing tools directly within their Splunk environment.

## Supported RSS Feeds

### Cloud Monitoring
1. AWS
2. GCP
3. Azure
4. IBM
5. Oracle Cloud
6. Digital Ocean

### Log Monitoring & APM
1. Splunk
2. Elastic
3. New Relic
4. SignalFx
5. Sentry
6. SumoLogic
7. sisdig

### Email & Other Apps
1. Office 365 (Microsoft)
   - 0365 Admin Centre
   - Power Platform Admin Centre
   - Microsoft Azure
2. Google Workspace
3. Zoho

### ITSM Tools
1. PagerDuty
2. Xmatters

### Audio / Video Conferencing Tools
1. Zoom
2. Google Meet
3. Webex
4. Bluejeans
5. Logmein

## Installation

1. Download the latest release of the Cloud Status Add-on.
2. Install the add-on in your Splunk environment using the Splunk web interface or CLI.
3. Configure the add-on to specify the RSS feeds you want to monitor.

Deployment Guide

Prerequisite : - Create a index --> cloudpulse

•	Single Instance 
(Pre-requisite) Cloud Status Addon for Splunk

•	Distributed deployment 
Heavy Forwarder – Cloud Status Addon for Splunk


## Configuration

1.	Deploy Apps and Addons as per Deployment Guide above.
2.	Navigate to config>> activation key
3. Data will get populate in cloudpulse index

## Usage

Once configured, the Cloud Status Add-on will automatically fetch data from the specified RSS feeds and index it into Splunk. You can then search, analyze, and visualize this data using Splunk's powerful features.

Note: Before enabling input, ensure that you create the index. In this case, we are using the "cloudpulse" name index. If you have a distributed environment, install the add-on on the Heavy Forwarder and the Cloud Status App on the Search Head.
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-cloud-status/bin/ta_cloud_status/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-cloud-status/bin/ta_cloud_status/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-cloud-status/bin/ta_cloud_status/aob_py3/markupsafe/_speedups.cpython-37m-x86_64-linux-gnu.so: this file does not require any source code
