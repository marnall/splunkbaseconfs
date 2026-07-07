# README for the Chameleon DataStage App for Splunk

## Table of Contents

- Overview
    - About the Chameleon DataStage App for Splunk
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

The Chameleon DataStage App for Splunk configures a Splunk deployment to process, visualize and analyze DataStage logs from DataStage endpoints.

### Chameleon DataStage App for Splunk

Author: Arcogent Inc.
Version: 1.0
Compatible Products:


Has Index-Time Operations? FALSE

Creates Indexes? FALSE

Below indexes have to be manually created after installing Chameleon DataStage App for Splunk

- Primary Index 1
    - Default Name: etl_datastage_jobinfo

- Primary Index 2
    - Default Name: etl_datastage_reportxml

- Primary Index 3
    - Default Name: etl_datastage_logsummary

Creates Inputs? FALSE

Does Summarization? FALSE

##### Scripts and Binaries

Binaries for DataStage (a.k.a ETL agent) should be downloaded from Arcogent [https://www.arcogent.com/products/chameleon/]. This is a prerequisite for the app to process DataStage logs.

NOTE: Please follow the instructions in the section "Pre-Installation Setup" to install ETL agent.

### Release Notes

Version 1.0 of the Chameleon DataStage App for Splunk:

- Supported and tested on Splunk Enterprise versions 6.2 or higher
- Supports all platforms and/or operating systems for Splunk servers
- Supports Distributed Splunk deployments
- Supports IBM Infosphere 9.x and 11.x series.

##### New Features


##### Fixed Issues

Version 1.0 of Chameleon DataStage App for Splunk includes:
- None

##### Known Issues

None.

##### Third-party Software

None. There are no third-party software or libraries in this application.

### Support and Resources

Additional help or documentations can be found on the [Arcogent website] (https://www.arcogent.com/products/chameleon/).

Users can visit the [Arcogent Support Portal](https://arcogent.com/support) and/or e-mail <a href="mailto:support@arcogent.com">support@arcogent.com</a> to create support requests related to any Arcogent products.

## Installation and Configuration

### Requirements

#### Prerequisites

Below are the  prerequisites for installing Chameleon DataStage App for Splunk.

1) Installing and setting up ETL Agent for DataStage.
2) Setting up source directories where ETL agent places the log files.

Note: These directories should be mentioned in inputs.conf in Chameleon DataStage App for Splunk before ingesting the data. These are the directories from which the App reads the DataStage log files.

#### Hardware Requirements

There are no hardware requirements for the Chameleon DataStage App for Splunk.

#### Software Requirements

SPLUNK
********
Splunk Enterprise 6.2 or later versions should be installed on the devices.

DataStage
*********
IBM Infosphere 9.x or 11.x should be installed in the environment.


#### Splunk Enterprise System Requirements

All of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply when using the Chameleon DataStage App for Splunk.

#### Download

Download the Chameleon DataStage App for Splunk from [here](https://www.arcogent.com/products/chameleon/).

### Installation Steps

This application should be installed on search heads if it is a distributed environment.

Regardless of the deployment model, there are no special steps required to install but there are steps required to configure this application after installing the Chameleon DataStage App for Splunk as described in Post-Installation Setup section.


### Configuration

#### Pre-Installation Setup

There are pre-installation steps required for this application.

##### Setting up source file directories

The file and/or directory structure should be configured for the ETL agent to output the DataStage log files. This becomes the source for Chameleon DataStage App for Splunk.

##### Installing ETL Agent

ETL Agent has to be downloaded from Arcogent.com and installed in the DataStage environment.

Following are the steps for installing the ETL Agent.

1) Download the appropriate version of the dsx executable required, based on your DataStage Version.
2) Open DataStage Designer Client for the project that you want to install Chameleon DataStage App in. Import the dowloaded file and while importing make sure that 'Overwrite without query' is not checked.
3) Verify that two job executables  'chameleon_driver' and 'chameleon_lgen' are listed.  Verify that the status for both is 'Does not yet exist'.
4) Set up import folder for DataStage Project so that jobs will be imported there and then execute /Jobs/Chameleon/chameleon_driver.
   Note:  If your DataStage installation path is non-standard, change the BIN_DIR parameter to the location of your DSEngine binaries.
5) Execute once with WRITE_UNCOMPLIED_JOBS='No'. During initial first ever execution, it would take several hours for the agent to retrieve logs. In a non-development environment, if you want to report on uncompiled jobs, execute chameleon_driver a second time with WRITE_UNCOMPLIED_JOBS='Yes'.
6) The above execution step can be automated by scheduled execution of chameleon_driver (with 'WRITE_UNCOMPILED_LOGS' set to 'No') as often as you want to get updates from your DataStage jobs.
   If you want to report on uncompiled jobs, schedule execution of chameleon_driver once per day with 'WRITE_UNCOMPILED_LOGS set to 'Yes'.

#### Post-Installation Setup

There are post-installation steps which are required for this application. They are described below.

In "Chameleon DataStage App for Splunk", under Configure Menu, there are three different configurations as shown below.

##### Base Configuration:

This configuration is mandatory.
The guided setup will facilitate the setting up of users and roles to control access to the dashboards.

##### Alert Configuration

This configuration is mandatory.
Using this utility, existing lookup file (containing Job Name and Run Time Threshold information) can be uploaded.

This utility is very important for the alert 'Job running greater than threshold time' to trigger. If not configured, this alert wouldn't be triggered.

###### Email Settings

For every alert, email aliases have to be configured so that alerts would be triggered and sent to email addresses mentioned.

##### Splunk Configuration

This configuration is not mandatory.
This utility should be used to override indexes or setting up source configuration.
The need for modifying the out-of-the-box default index names can arise when the app needs to be tested in different environments or indexes need to be seggregated based on DataStage projects.

#### Multi-Tenancy Support

This app can be augmented or extended to allow for multi-tenancy, i.e., separating data from multiple user groups and/or customers into access-controlled indexes.

## User Guide

### Concepts

The Chameleon DataStage App for Splunk configures a Splunk deployment to process, analyze and visualize DataStage log data. The Chameleon DataStage App for Splunk configures the
default indexes, sourcetypes and source information for DataStage log data.

DataStage log data from ETL agent gets ingested into Chameleon DataStage App as three primary sourcetypes, jobinfo, dstagexml and logsum.

The default data format for DataStage log events are as follows.

1) Single line XML event at Job level (.JobInfo file)
2) Single line XML event for every notification type like WARNING, FATAL, INFO etc. (.LogSum file)
3) Multiline XML event starting for every Stage within a Job (.XML file)
4) Multiline XML event corresponding to Job parameters information. (.XML file)

### Index-Time Operations

The Chameleon DataStage App for Splunk does not perform any index-time operations.

#### Host Metadata Field Overwriting

There is no host metadata field overwriting

#### Sourcetype Metadata Field Overwriting

The Sourcetype metadata field is set with default 'dstagexml' for occurence of events corresponding to a stage within .XML file.

The overwriting occurs for events corresponding to job parameters information in .XML file.

For example, Chameleon creates sourcetype 'paramset' in place of the default sourcetype 'dstagexml' when it finds occurence of <ParamSet> xml tag.


### Data Inputs

The Chameleon DataStage App for Splunk defines three external data sources pertaining to DataStage log data.
1) .JobInfo file
2) .LogSum File
3) .XML file.

### Macros

The Chameleon DataStage App for Splunk defines 3 macros. These macros are used for facilitating the seamless execution of search queries

### Lookups / KV Stores

The Chameleon DataStage App for Splunk contains 2 KV Stores which are described below.

1) application_splunk_lookup
   This KV Store maintains the relationship between index, sourcetype, source and macro name. This KV Store gets updated when any index information is updated in
   "Application Splunk Configuration" under "Configure" menu.

2) application_alert_threshold_lookup
   This KV Store maintains the relationship between Job name and Run time threshold. This KV Store gets updated when Job Name and their thresholds are configured
   using "Application Alert Configuration" under "Configure" menu.


### Datamodels

The Chameleon DataStage App for Splunk contains zero datamodels.

### Saved Searches

The Chameleon DataStage App for Splunk contains 5 saved searches out of which 3 of them are related to scheduled alerts for .JobInfo file.  The other 2 saved searches are
related to scheduled alerts for .LogSum file.

Scheduled alerts for .JobInfo File
***********************************
1) Jobs with Errors
   This alert is scheduled every hour at 45th minute. The saved search looks for any Jobs with error statuses in last 1 hour and triggers the alert
   when it finds any events.

2) Job running greater than threshold time
   This alert is scheduled every hour at 45th minute. For this alert to work, Jobs and their runtime thresholds have to be configured using "Application Splunk
   Configuration" in "Configure" menu. The saved search looks for any Jobs whose execution or run time is more than the threshold time configured in last 1 hour
   and triggers the alert.

3) Job Run Time greater than 7 day average of previous run times  (for successful jobs)
   This alert is scheduled every hour at 15th minute. The saved search looks for any successful Jobs in the last 1 hour whose running times is greater than average of it's
   running times in the past 7 days and triggers the alert.

Scheduled alerts for .LogSum File
**********************************
1) Warnings increased in current Job Run compared to previous run
   This alert is scheduled every hour at 15th minute. The saved search looks for any Jobs in the last 1 hour where number of warnings in the current job run are greater than average of it's
   that in the previous run before the last hour.

2) Errors increased in current Job Run compared to previous run
   This alert is scheduled every hour at 15th minute. The saved search looks for any Jobs in the last 1 hour where number of errors in the current job run are greater than average of it's
   that in the previous run before the last hour.

### Troubleshooting

Once the DataStage log files start arriving at the source, the ingestion of data into Chameleon DataStage App would start. To troubleshoot whether the
data is ingested successfully, navigate to "Base Configuration" under "Configure Menu". Using guided setup, navigate to "Check Data" where information can be
found on the ingested data.

If the data is shown to be ingested successfully, then the three searches as mentioned on "Check Data" page can be run on splunk search to further look at the fields
extracted.

After running the searches, below dashboards can be checked after ingestion of the corresponding DataStage log file as shown below.

1) Executive Dashboard (JobInfo File)
2) System Administrative Dashboard (LogSum File)
3) Developer Dashboard (XML file)


NOTE : Executive and System Administrative Dashboard displays reports with data from past 1 month while the Developer Dashboard displays reports with data since a day
before.

### Upgrading

There are no special steps to upgrade the Chameleon DataStage App for Splunk. Any release-specific steps will be detailed in the release notes when they appear.