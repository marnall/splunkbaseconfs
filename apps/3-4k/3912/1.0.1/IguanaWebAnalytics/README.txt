# README for the Iguana Web Analytics App for Splunk

## Table of Contents

- Overview
    - About the Iguana Web Analytics App for Splunk
    - Release Notes
    - Support and Resources
- Installation and Configuration
    - Requirements
    - Installation steps
    - Configuration
- User Guide
    - Concepts
    - Index-Time Operations
    - Data Inputs
    - Lookups / KV Stores
    - Datamodels
    - Saved Searches
    - Troubleshooting
    - Upgrading

-----

## Overview

Iguana Web Analytics App for Splunk configures a Splunk deployment which provides capabilities like data inputs configuration and knowledge objects on web analytics.

### Iguana Web Analytics App for Splunk

Author: Arcogent Inc.
Version: 1.0.1
Compatible Products:


Has Index-Time Operations? FALSE

Creates Indexes? FALSE

Below indexes have to be manually created after installing Iguana Web Analytics App for Splunk

- Primary Index
    - Default Name: iwa

Creates Inputs? FALSE

Does Summarization? FALSE

##### Scripts and Binaries

There are no scripts or binaries associated with this app.

### Release Notes

Version 1.0 of the Iguana Web Analytics App for Splunk:

- Supported and tested on Splunk Enterprise versions 6.6 or higher
- Supports only Linux operating systems for Splunk servers
- Supports only single Splunk instance deployments

##### New Features


##### Fixed Issues

Version 1.0 of Iguana Web Analytics App for Splunk includes:
- None

##### Known Issues

None.

##### Third-party Software

None. There are no third-party software or libraries in this application.

### Support and Resources

Additional help or documentations can be found on the [Arcogent website] (https://www.arcogent.com/products/

Users can visit the [Arcogent Support Portal](https://arcogent.com/support) and/or e-mail <a href="mailto:support@arcogent.com">support@arcogent.com</a> to create support requests related to any Arcogent products.

## Installation and Configuration

### Requirements

#### Prerequisites

Below are the  prerequisites for installing Iguana Web Analytics App for Splunk.

1) Setting up source directories where source data files are present.

Note: This source directory would be used in "Configure Source" configuration screen in Iguana Web Analytics App for Splunk.

#### Hardware Requirements

There are no hardware requirements for the Iguana Web Analytics App for Splunk.

#### Software Requirements

SPLUNK
********
Splunk Enterprise 6.6 or later versions should be installed on the devices.

#### Splunk Enterprise System Requirements

All of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply when using the Iguana Web Analytics App for Splunk.

#### Download

Download the Iguana Web Analytics App for Splunk from Splunkbase.

### Installation Steps

This application should be installed on a single Splunk instance.

There are steps required to configure this application after installing the Iguana Web Analytics App for Splunk as described in Post-Installation Setup section.

### Configuration

#### Pre-Installation Setup

There are pre-installation steps required for this application.

##### Setting up source file directories

The file and/or directory structure within the local system should be configured. This becomes the source for Iguana Web Analytics App for Splunk to pick up data files.
This directory structure and file information will be provided in the "Configure Source" configuration in Iguana Web Analytics App for Splunk.

#### Post-Installation Setup

There are post-installation steps which are required for this application. They are described below.

In "Iguana Web Analytics App for Splunk", under Configuration Menu, there is "Configure Source" configuration menu. In this configuration,
below information has to be provided.

1) Report Suite
2) File Delivery, Delivery Schedule and Delivery Method.
3) License
4) Index Name
5) User Name

#### Multi-Tenancy Support

This app can be augmented or extended to allow for multi-tenancy, i.e., separating data from multiple user groups and/or customers into access-controlled indexes.

## User Guide

### Concepts

The Iguana Web Analytics App for Splunk configures a Splunk deployment to facilitate the data ingestion. The Iguana Web Analytics App for Splunk also provides 
knowledge objects like alerts, dashboards and reports pertaining to web analytics.

### Index-Time Operations

The Iguana Web Analytics App for Splunk does not perform any index-time operations.

#### Host Metadata Field Overwriting

There is no host metadata field overwriting

#### Sourcetype Metadata Field Overwriting

There is no sourcetype metadata field overwriting.

### Data Inputs

The Iguana Web Analytics App for Splunk expects two data inputs.

1) Clickstream data file 
   The data file should be dated and available as .tgz file. This zip file contains .tsv data file within.
2) Lookup data file
   The lookup data file should be dated and available as .tgz file. This zip file contains all the lookup files which are in .tsv format.

### Macros

The Iguana Web Analytics App for Splunk contains 1 macro.

1) iwa_index
This macro is used to define the index "iwa". It is used in all the data models in the search string.

### Lookups / KV Stores

The Iguana Web Analytics App for Splunk does not contain any lookups or KV Stores.


### Datamodels

The Iguana Web Analytics App for Splunk contains four datamodels which are described below.

1) Visit Info
   This data model captures information related to all the visits.
   
2) Page Statistics
   This data model contains information about page names, page urls and other page specific information.
   
3) Purchase
   This data model contains information related to purchase specific actions performed while visiting the website.
   
4) Action
   This data model contains information related to all the actions performed by the visitor

### Saved Searches

The Iguana Web Analytics App for Splunk contains several saved searches which are fired as scheduled alerts.

1) Bots (Occurence of same IP consecutively more than 10 times) in Last 1 day
   When there is occurrence of bots that is occurrence of same ip address in consecutive visit data in last 1 day, alert is fired .

2) Bounce Rate Greater Than 60 Percent in Last 1 Day
   When the bounce rate is greater than 60 percent (industry standard average bounce rate) as seen in last 1 day, alert is fired.

3) Pages and their Page views in Last 1 Day
   Alert is fired as a static report containing pages and their page views as seen in Last 1 Day.
   
4) Paid Search Keywords in Last 1 Day
   Alert is fired as a static report containing all the keywords used in paid searches as seen in Last 1 Day.

5) Return Visitors Less Than 30 Percent in Last 7 Days
   If the percentage of return visitors is less than 30 percent (industry average), then the alert is fired.

6) Searched Keywords in Last 1 Day
   Alert is fired as a static report containing all the search keywords used in Last 1 Day. 

7) Visitor Count of yesterday less than previous 5 days Average
   Alert is fired if the visitor count in last 1 day is less than that of previous 5 days average. 

8) Visitor Count yesterday exceeded peak of Previous 5 days.
   Alert is fired if the visitor count in last 1 day exceeds the peak value of visitor count found in previous 5 days average. 


### Troubleshooting

After the data ingestion is configured in "Configuration" and data ingestion is started, first step in troubleshooting is to check if the data is ingested
by checking index=iwa sourcetype=omniture. 

Also internal index can be searched for data like below.
index=_internal sourcetype=splunkd 'Iguana'

Also the dashboards under "Market Intelligence" menu would have reports showing up after data is ingested.

Note : The supporting add-ons Iguana Web Analytics Technical Add-On for Adobe Analytics and Iguana Web Analytics Support Add-On for Adobe Analytics
are  already installed before configuration.

### Upgrading

There are no special steps to upgrade the Iguana Web Analytics App for Splunk. Any release-specific steps will be detailed in the release notes when they appear.