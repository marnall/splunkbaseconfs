# README for the Iguana Web Analytics Support Add-on for Adobe® Analytics

## Table of Contents

- Overview
    - About the Iguana Web Analytics Support Add-on for Adobe® Analytics
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

The Iguana Web Analytics Support Add-on for Adobe® Analytics configures a Splunk deployment to add knowledge objects providing insights on adobe analytics data.

### Iguana Web Analytics Support Add-on for Adobe® Analytics

Author: Arcogent Inc.
Version: 1.0.2
Email: support@arcogent.com
Compatible Products:


Has Index-Time Operations? FALSE

Creates Indexes? FALSE

Creates Inputs? FALSE

Does Summarization? FALSE

##### Scripts and Binaries

There are no scripts or binaries associated with this app.

### Release Notes

Version 1.0 of the Iguana Web Analytics Support Add-on for Adobe® Analytics:

- Supported and tested on Splunk Enterprise versions 6.6 or higher
- Supports only Linux platform for Splunk servers
- Supports only single instance Splunk deployments

##### New Features


##### Fixed Issues

Version 1.0 of Iguana Web Analytics Support Add-on for Adobe® Analytics includes:
- None

##### Known Issues

None.

##### Third-party Software

None. There are no third-party software or libraries in this application.

### Support and Resources

Additional help or documentations can be found on the [Arcogent website] (https://www.arcogent.com/products/

## Installation and Configuration

### Requirements

#### Prerequisites

Below are the  prerequisites for installing Iguana Web Analytics Support Add-on for Adobe® Analytics.

1) Installing and setting up Iguana Web Analytics App For Splunk.
2) Installing and setting up Iguana Web Analytics Technical Add-On For Splunk.

#### Hardware Requirements

There are no hardware requirements for the Iguana Web Analytics Support Add-on for Adobe® Analytics.

#### Software Requirements

SPLUNK
********
Splunk Enterprise 6.6 or later versions should be installed on the devices.

#### Splunk Enterprise System Requirements

All of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply when using the Iguana Web Analytics Support Add-on for Adobe® Analytics.

#### Download

Download the Iguana Web Analytics Support Add-on for Adobe® Analytics from Splunkbase.

### Installation Steps

This application should be installed on single Splunk instance. Installation is not supported on distributed or clustered environments.

There are no special steps required to install this app.

### Configuration

#### Pre-Installation Setup

There are no pre-installation steps required for this application.

##### Setting up source file directories

There is no process to set up source file directories.

#### Post-Installation Setup

There are no post-installation steps which are required for this application.

###### Email Settings

For every alert, email aliases have to be configured so that alerts would be triggered and sent to email addresses mentioned.

#### Multi-Tenancy Support

This app can be augmented or extended to allow for multi-tenancy, i.e., separating data from multiple user groups and/or customers into access-controlled indexes.

## User Guide

### Concepts

The Iguana Web Analytics Support Add-on for Adobe® Analytics configures a Splunk deployment to provide insights on Adobe clickstream data through different
knowledge objects specific to Adobe clickstream. 


### Index-Time Operations

The Iguana Web Analytics Support Add-on for Adobe® Analytics does not perform any index-time operations.

#### Host Metadata Field Overwriting

There is no host metadata field overwriting

#### Sourcetype Metadata Field Overwriting

There is no sourcetype metadata field overwriting.

### Data Inputs

There are no external data inputs within this app.

### Macros

The Iguana Web Analytics Support Add-on for Adobe® Analytics contains several macros. These macros are used for facilitating the KV lookup searches.

Below is the list of macros.

1) iwa_adobe_browser
   This macro does an inputlookup on KV store iwa_adobe_browser_lookup and outputs the fields from KV store.  	
2) iwa_adobe_color_depth
   This macro does an inputlookup on KV store iwa_adobe_color_depth_lookup and outputs the fields from KV store. 
3) iwa_adobe_connection_type
   This macro does an inputlookup on KV store iwa_adobe_connection_type_lookup and outputs the fields from KV store. \
4) iwa_adobe_country
   This macro does an inputlookup on KV store iwa_adobe_country_lookup and outputs the fields from KV store. 
5) iwa_adobe_event
   This macro does an inputlookup on KV store iwa_adobe_event_lookup and outputs the fields from KV store. 
6) iwa_adobe_javascript_version
   This macro does an inputlookup on KV store iwa_adobe_javascript_lookup and outputs the fields from KV store. 
7) iwa_adobe_languages
   This macro does an inputlookup on KV store iwa_adobe_languages_lookup and outputs the fields from KV store. 
8) iwa_adobe_plugins
   This macro does an inputlookup on KV store iwa_adobe_plugins_lookup and outputs the fields from KV store. 
9) iwa_adobe_referrer_type
   This macro does an inputlookup on KV store iwa_adobe_referrer_type_lookup and outputs the fields from KV store. 
10)	iwa_resolution
    This macro does an inputlookup on KV store iwa_adobe_resolution_lookup and outputs the fields from KV store. 
11) iwa_adobe_search_engines
    This macro does an inputlookup on KV store iwa_adobe_search_engines_lookup and outputs the fields from KV store. 
12) iwa_adobe_customize_variables
    This macro does an inputlookup on KV store iwa_adobe_customize_variables_lookup and outputs the fields from KV store. 

### Lookups / KV Stores

The Iguana Web Analytics Support Add-on for Adobe® Analytics contains several KV Stores which are described below.

1) iwa_adobe_states_lookup
2) iwa_adobe_ingest_lookup
3) iwa_adobe_browser_lookup
4) iwa_adobe_color_depth_lookup
5) iwa_adobe_connection_type_lookup
6) iwa_adobe_country_lookup
7) iwa_adobe_event_lookup
8) iwa_adobe_javascript_version_lookup
9) iwa_adobe_languages_lookup
10)	iwa_adobe_plugins_lookup
11)	iwa_adobe_referrer_type_lookup
12)	iwa_resolution_lookup
13) iwa_adobe_search_engines_lookup
14) iwa_adobe_customize_variables_lookup



### Datamodels

The Iguana Web Analytics Support Add-on for Adobe® Analytics contains zero datamodels. The saved searches and dashboard searches refer to data models
whose definitions are in Iguana Web Analytics App for Splunk.

### Saved Searches

The Iguana Web Analytics Support Add-on for Adobe® Analytics contains several saved searches (alerts) which are described below. These alerts would be visible
under "Alerts" in Iguana Web Analytics App for Splunk.

1) Cart Activities In Last 1 Day
   This alert is scheduled every day at 1 AM. The saved search looks for any cart activities in last 1 day and fires the alert if any results found. The cart
   activities include cart adds, cart removes, cart views and checkouts.

2) Custom Events In Last 1 Day
   This alert is scheduled every day at 1 AM. This saved search looks for custom events that occured in last 1 day and fires the alert accordingly.

3) Internet Connection Used By Visitors in Last 1 Day
   This alert is scheduled every day at 1 AM. This saved search reports on internet connections used by visitors in last 1 day and fires the alert accordingly.

4) Outliers in Visitors By Country In Last 7 Days
   This alert is scheduled every day at 1 AM. This saved search looks for anomalies or outliers in number of visitors corresponding to a country in last 7 days and fires the alert accordingly.
   Outliers are typically the spikes in visitor count corresponding to a country as compared to visitor count of other countries.

5) Outliers in Visitors based on the Language in last 7 days
   This alert is scheduled every day at 1 AM. This saved search looks for anomalies or outliers in number of visitors corresponding to the language of websites they visited in last 7 days 
   and fires the alert accordingly. Outliers are typically the spikes in visitor count corresponding to language of websites as compared
   to visitor count of other languages.

6) Page Views For Paid Search Engines in Last 1 Day
   This alert is scheduled every day at 1 AM. This saved search reports on number of pageviews occurred using paid search engines in last 1 day and fires the alert accordingly.

7) Top 10 Browsers in Last 1 day
   This alert is scheduled every day at 1 AM. This saved search reports on top 10 browsers in last 1 day and fires the alert accordingly.

8) Top 10 Languages based on Page Views in Last 1 Day
   This alert is scheduled every day at 1 AM. This saved search reports on top 10 langauges in last 1 day corresponding to number of pageviews the language of websites get and fires the alert accordingly.

9) Top 10 Operating Systems in Last 1 Day
   This alert is scheduled every day at 1 AM. This saved search reports on top 10 operating systems in last 1 day and fires the alert accordingly.

10) Top Search Engines in Last 1 Day
    This alert is scheduled every day at 1 AM. This saved search reports on top 10 search engines in last 1 day and fires the alert accordingly.

11) Total Revenue By Languages in Last 1 Day
    This alert is scheduled every day at 1 AM. This saved search reports total revenue in last 1 day corresponding to each language of the websites and fires the alert accordingly.

### Troubleshooting

Once this SA is deployed, navigate to "Market Intelligence" from the menu within Iguana Web Analytics App for Splunk. 

Within this menu, a section called "Adobe ClickStream" will now be made available with dashboards and reports now showing up. Also alerts specific to this apps 
would be visibe in "Alerts" in Iguana Web Analytics App for Splunk.


### Upgrading

There are no special steps to upgrade the guana Web Analytics Support Add-on for Adobe® Analytics. Any release-specific steps will be detailed in the release notes when they appear.