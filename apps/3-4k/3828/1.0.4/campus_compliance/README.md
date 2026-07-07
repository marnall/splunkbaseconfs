# Campus Compliance Toolkit for NIST 800-171

## Overview

|                           |                                                                        |
| ------------------------- | ---------------------------------------------------------------------- |
| Author                    | Aplura, LLC                                                            |
| App Version               | 1.0.2                                                                  |
| App Build                 | 37                                                                     |
| Has index-time operations | false                                                                  |
| Creates an index          | false                                                                  |
| Implements summarization  | Currently, the app does not generate summaries                         |
| Data Models               | This App makes use of Data Models, and expects them to be accelerated. |

About this App

# Installation and Configuration

## Software requirements

### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

## Download

Download Campus Compliance Toolkit for NIST 800-171 at [https://splunkbase.splunk.com/app/3828/](https://splunkbase.splunk.com/app/3828/).

### Prerequisites

This app requires the [Splunk Common Information Model (CIM) Add-on](https://splunkbase.splunk.com/app/1621/) to be installed. For information regarding the installation of the CIM Add-on, please see the [Splunk Common Information Model Add-on documentation](http://docs.splunk.com/Documentation/CIM/4.9.1/User/Overview).

### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1.  Deploy as you would any App, and restart Splunk.
2.  Configure.

### Deploy to Splunk Cloud

1.  Contact Splunk Cloud Support for assistance with the installation.

### Deploy to a Distributed Environment

1.  This app should be distributed only to search heads on which you would like to use this app.

### Search Head Clustering

1.  This app should be compatible with Splunk Search Head Clustering.

### Data Model Acceleration

While not required, it is highly recommended, and the default, to use Data Model Acceleration with this App, for performance reasons. See the Data Models section for more information about which data models should be accelerated.

### A note on Splunk Data Model Acceleration and Disk Space

This app requires data model acceleration, which will use additional disk space. If you are using the Splunk App for Enterprise Security, this is already enabled, and should have been factored into your retention policies. If not, you should review the documentation on data model acceleration, how it uses disk space, and how to plan for it. This documentation can be found here: [Data Model Summary Size On Disk](http://docs.splunk.com/Documentation/Splunk/latest/Knowledge/Acceleratedatamodels#Data_model_summary_size_on_disk).

# User Guide

## Key concepts for Campus Compliance Toolkit for NIST 800-171

This app is designed to assist organizations with reaching compliance with the NIST 800-171 standards. Where Splunk can be applied to these standards, dashboards have been created using the [Common Information Model](http://docs.splunk.com/Documentation/CIM/4.9.1/User/Overview) for normalizing event data. This means that for the app to provide dashboard results, your data must be properly onboarded, and have the appropriate tags to be consumed by the data model. See the Data Model Acceleration section of the documentation for more information, as well as the table for individual controls.

## Data Models

This app uses the following Data Models:

  - Application_State
  - Authentication
  - Change_Analysis
  - Intrusion_Detection
  - Malware
  - Network_Sessions
  - Network_Traffic
  - Performance
  - Updates
  - Vulnerabilities
  - Web

## Macros

The following macros can be used to configure the app.

### cc_allowed_ports

Contains the name of the lookup which states which ports are considered allowed for reports.

### cc_get_indexers

Contains a search pattern which returns the indexers for the environment.

### cc_get_searchheads

Contains a search pattern which returns the search heads for the environment.

### cc_inactive_time

Contains the time span, in seconds after which an account is considered inactive. Defaults to 31536000 seconds (one year).

### cc_internal_ranges

Returns a search pattern which indicated which traffic is considered internal traffic. Takes an argument which should be the field name which is being compared (src, dest, src_ip, dest_ip).

### cc_max_review_age

Contains the time span, in seconds, which is considered the review period for the control dashboards in the application. Defaults to 172800 seconds (two days).

### cc_prestats

Used to control how the tstats command, when using prestats option, is called within the application.

### cc_priv_lookup

Contains the definition of a lookup which contains the list of users which is considered privileged in the environment.

### cc_timeSync_allowance

Contains the time span, in seconds, in which is expected systems will synchronize time. Defaults to 86400 (one day).

### cc_tstats

Used to control how the tstats command, when not using prestats option, is called within the application.

## Lookups

The following lookups can be used to configure the app.

### cc_allowed_ports

File name: cc_allowed_ports.csv

This lookup is used for controlling which network ports are considered allowed when viewing reports. The dvc field is wild-carded to allow for the creation of allowed ports across multiple devices.

### cc_allowed_processes

File name: cc_allowed_processes.csv

This lookup is used for controlling which processes are considered allowed when viewing reports. The dest field is wild-carded to allow for whitelisting processes across multiple destinations.

### cc_priv_users

File name: cc_priv_users.csv

A list of users which are considered privileged users in the applicable environment.

### cc_splunk_data_controls

File name: cc_splunk_data_controls.csv

A lookup which allows for the control of data sources which are considered missing. The index, host, and sourcetype fields are wild-carded.

# Control Dashboards

## 3.1.1 Limit system access to authorized users

Data model: Authentication

## 3.1.6 Use of non-privileged accounts

Data model: Authentication

## 3.1.7 Prevention of privileged functions

Data model: Authentication

## 3.1.8 Unsuccessful logon attempts

Data model: Authentication, Change_Analysis

## 3.1.12 Monitor remote access

Data model: Network_Sessions

## 3.1.20 Use of external systems

This dashboard can be used to provide links to additional Splunk apps which may contain relevant information. By default this provides a link the Splunk App for AWS.

## 3.1.21 Portable storage

The CIM does not currently contain a model for these events. Events to populate this dashboard should be tagged with the following tags:

  - usb
  - storage

Eventtypes and tags have been included for Windows and Linux USB storage insertions.

## 3.3.1 Create protect and retain audit records

Provides an overview of Splunk index retention settings and results.

## 3.3.2 User action audit

Data model: Change_Analysis

## 3.3.3 Audit event reviews

Data model: Splunk_Audit

Provides a report on the last time the relevant dashboards in the app were viewed, and if they need to be reviewed again.

## 3.3.4 Audit failure alerts

Data model: Change_Analysis

Uses Splunks _internal index.

## 3.3.5 Audit event monitoring

Data model: Authentication, Network_Traffic, Vulnerabilities, Malware, Intrusion_Detection

## 3.3.6 On-demand audit analysis and reporting

Provides a link to the Search and Reporting app.

## 3.3.7 Time synchronization

Data model: Performance, Application_State

## 3.3.8 Protect audit information and tools

Uses REST commands to gather information on Splunk users.

## 3.3.9 Limit audit management users

Uses REST commands to gather information on Splunk users.

## 3.4.6 Least functionality

Data model: Application_State

## 3.4.7 Nonessential functions ports protocols and services

Data model: Network_Traffic

## 3.4.8 Default deny

Data model: Application_State

## 3.4.9 Control and monitor user installed software

Data model: Application_State

Software installation is not covered by the current version of the CIM. The panels will display events tagged with the following tags:

  - software
  - installation

Eventtypes and tags for Windows (MSI) installations have been included in this app.

tag=installation tag=software

## 3.5.6 Identifier inactivity

Data model: Authentication

## 3.8.7 Removable media

The CIM does not currently contain a model for these events. Events to populate this dashboard should be tagged with the following tags:

  - usb
  - storage

Eventtypes and tags have been included for Windows and Linux USB storage insertions.

## 3.11.2 Vulnerability scanning

Data model: Vulnerabilities

## 3.11.3 Vulnerability remediation

Data model: Vulnerabilities

To effectively drive this dashboard, Vulnerability events should have the following knowledge objects

| Knowledge Object | Value/Name         | Type       |
| ---------------- | ------------------ | ---------- |
| tag              | campus_compliance | N/A        |
| tag              | vulnerability      | N/A        |
| field            | is_mitigated      | true/false |
| field            | first_seen        | epoch time |
| field            | last_seen         | epoch time |

3.11.3 Knowledge Objects

## 3.12.3 Control effectiveness

Pending

## 3.13.1 Boundary protection

Data model: Network_Traffic

## 3.13.13 Mobile code

Data model: Web

## 3.14.1 Flaw handling

Data model: Updates, Application_State

## 3.14.3 Alert monitoring

Data model: Intrusion_Detection, Malware

## 3.14.4 Protection updates

Data model: Malware.Malware_Operations

## 3.14.5 File and malware scanning

Data model: Malware

## 3.14.6 Traffic monitoring

Data model: Network_Traffic

## 3.14.7 Unauthorized use

Pending

# Release notes

  - Initial Version

<!-- end list -->

  - Added correct URL to Documentation
  - CC-34 - Fix failed App Inspect Errors

## About this release

Version 1.0.2 of Campus Compliance Toolkit for NIST 800-171 is compatible with:

|                            |                   |
| -------------------------- | ----------------- |
| Splunk Enterprise versions | 6.6, 7.0          |
| Platforms                  | Splunk Enterprise |

Compatability

## Known Issues

Version 1.0.2 of Campus Compliance Toolkit for NIST 800-171 has the following known issues:

  - None

# Event Generator

No event generator is shipped with this app.

# Support and resources

## Questions and answers

Access questions and answers specific to Campus Compliance Toolkit for NIST 800-171 at [https://answers.splunk.com](https://answers.splunk.com) . Be sure to tag your question with the App.

## Support

  - Support Email: [undefined@splunk.com](mailto:undefined%40splunk.com)
  - Support Offered: Community Engagement

# License

This app has been released under the GNU General Public License, Version 2. Please see this included license.txt for more details.

# Third Party Notices

Version 1.0.2 of Campus Compliance Toolkit for NIST 800-171 incorporates the following Third-party software or third-party services.

## Aplura, LLC Components

Components Written by Aplura, LLC Copyright (C) 2016-2017 Aplura, ,LLC

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, eMA 02110-1301, USA.

## markdown.js

Released under the MIT license.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the Software), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## jquery.js

[https://github.com/jquery/jquery/blob/master/LICENSE.txt](https://github.com/jquery/jquery/blob/master/LICENSE.txt)

Copyright JS Foundation and other contributors, [https://js.foundation/](https://js.foundation/)

This software consists of voluntary contributions made by many individuals. For exact contribution history, see the revision history available at [https://github.com/jquery/jquery](https://github.com/jquery/jquery)

The following license applies to all parts of this software except as documented below:

-----

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the Software), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

-----

All files located in the node_modules and external directories are externally maintained libraries used by this software which have their own licenses; we recommend you read them, as their terms may differ from the terms above.

## d3.js

[https://github.com/d3/d3/blob/master/LICENSE](https://github.com/d3/d3/blob/master/LICENSE)

Copyright 2010-2016 Mike Bostock All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

  - Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
  - Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
  - Neither the name of the author nor the names of contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS AS IS AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

## fontawesome

Pulled from fontawesome.io/license/

### Font License

Applies to all desktop and webfont files in the following directory: font-awesome/fonts/. License: SIL OFL 1.1 URL: [http://scripts.sil.org/OFL](http://scripts.sil.org/OFL)

### Code License

Applies to all CSS and LESS files in the following directories: font-awesome/css/, font-awesome/less/, and font-awesome/scss/. License: MIT License URL: [http://opensource.org/licenses/mit-license.html](http://opensource.org/licenses/mit-license.html)

### Documentation License

Applies to all Font Awesome project files that are not a part of the Font or Code licenses. License: CC BY 3.0 URL: [http://creativecommons.org/licenses/by/3.0/](http://creativecommons.org/licenses/by/3.0/)

### Related Topics

  - [Documentation overview](index.html#document-index)

2017, Aplura, LLC. | Powered by [Sphinx 1.6.4](http://sphinx-doc.org/) & [Alabaster 0.7.10](https://github.com/bitprophet/alabaster)
