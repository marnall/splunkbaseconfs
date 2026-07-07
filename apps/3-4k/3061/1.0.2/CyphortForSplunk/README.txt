## Table of Contents

### OVERVIEW

- About Cyphort For Splunk
- Release notes
- Performance benchmarks
- Support and resources

### INSTALLATION

- Hardware and Software Requirements
- Installation steps
- Deploy to a Single Server Instance
- Deploy to a Distributed Deployment
- Deploy to a Distributed Deployment with Search Head Clustering
- Deploy to Splunk Cloud


### USER GUIDE

- Data types
- Lookups
- Configure Cyphort For Splunk
- Troubleshooting
- Upgrade

---
### OVERVIEW

#### About Cyphort For Splunk

| About | Cyphort For Splunk |
| --- | --- |
| Developer | Aplura, LLC |
| App Version | 1.0.2 |
| App Build | 204 |
| TA | TA-CyphortForSplunk |
| IA | IA-CyphortForSplunk |
| Folder Name | CyphortForSplunk |
| Vendor Products | Cyphort API 3.3.0 |
| Has index-time operations | true
| Create an index | false |
| Implements summarization | false |

Cyphort For Splunk allows a Splunk® Enterprise administrator to integrate with the Cyphort Advanced Intrusion Detection API and pull the relevant incidents.

##### Scripts and binaries

The following list of scripts are used to interact with the data being aquired.

- $SPLUNK_HOME/etc/apps/CyphortForSplunk/bin/CyphortForSplunk.py
    - The Modular Input used to communicate and consume the API data
- $SPLUNK_HOME/etc/apps/CyphortForSplunk/bin/ModularInput.py
    - The Modular Input Class to consume and populate Splunk with Data.
- $SPLUNK_HOME/etc/apps/CyphortForSplunk/RESTClient.py
    - The REST Client Base Class to interact with the Cyphort API.

#### Release notes

These are the issues that were closed for version 1.0.2.

Release Notes - Cyphort - Version Cyphort-v1.0.2


* Bug
    * [CYP-49] - API Doesn't Pull Events Correctly
    * [CYP-51] - Fix Display of last_activity_time
    * [CYP-52] - Fix Incident Detail View
    * [CYP-53] - Windows Rest Client Fails
    * [CYP-60] - App Health -- event retrieval results not limited to 24 hours
    * [CYP-62] - Duplicated Events from API
    * [CYP-70] - Custom Cell Renderer Expansion
    * [CYP-71] - Incident Detail Doesn't Display Raw Event Details

* Improvement
    * [CYP-39] - v1.0.2 Documentation
    * [CYP-40] - App Certification Failures
    * [CYP-48] - Configure View to hide "incident_key" field
    * [CYP-50] - Update Cyphort API Result
    * [CYP-55] - Modular Input - Checkpoint incidents

* New Feature
    * [CYP-68] - Create 6.5 Monitoring Console Health Checks 

* Task
    * [CYP-63] - Correct issues with the About page

* Sub-task
    * [CYP-41] - Errors relating to Eventgen
    * [CYP-42] - Modular Input
    * [CYP-43] - Lookups
    * [CYP-44] - Dependency Documentation
    * [CYP-45] - Support Contact Information
    * [CYP-46] - Logging Configurations
    * [CYP-47] - Multiple READMEs
    * [CYP-64] - Remove punctuation in improper places
    * [CYP-65] - Reword instructions for clarification
    * [CYP-66] - README.md formatting issues
    * [CYP-67] - Minor changes to overall document
    
These are the issues that were closed for version 1.0.1.

 * Bug
    * [CYP-16] - Generate Lookups is failing UI testing
    * [CYP-25] - Discrepancy between data on incident overview and incident detail
    * [CYP-26] - Remove Malware Overview Dashboard
    * [CYP-32] - Last 5 Event Retrieval Doesn't Show Right Timestamp
    * [CYP-33] - Selecting Incident from Top 10 Threats on Overview Doesn't Display Correct on Details
    * [CYP-36] - Unsupported Search Structures in 6.2
    * [CYP-37] - Incident ID search results throws errors in Incident details tab

* Improvement
    * [CYP-15] - v1.0.1 Documenation
    * [CYP-17] - App Certification Failures
    * [CYP-22] - Convert Panels to Pre-Built Panels
    * [CYP-23] - Update Documentation
    * [CYP-24] - Update Modular Input Validation
    * [CYP-27] - Update documentation for pre-built panels
    * [CYP-28] - Split app health checkpoints panel by host
    * [CYP-29] - Link in configuration menu to data input page
    * [CYP-30] - Add Data Input Dropdown to Incident Overview
    * [CYP-35] - Integer Only Axis Label.
    * [CYP-38] - Remove Administrator Functions

* Sub-task
    * [CYP-18] - [ failure ] Check that all executable files only exist in the /bin directory of the app.
    * [CYP-20] - [ failure ] Check a valid scheme is returned via the scripts via the scheme command when using a modular input.
    * [CYP-21] - [ failure ] Check the scheme arguments match the inputs.conf.spec file when using a modular input.

These are the issues that were closed for version 1.0.0.

* Bug
    * [CYP-13] - Custom Cell Renderer fails on 6.2

* Improvement
    * [CYP-7] - Documentation
    * [CYP-11] - Update Overview Dashboard
    * [CYP-12] - Update Incidents Overview

* New Feature
    * [CYP-3] - Admin Panels
    * [CYP-4] - Incident Overview
    * [CYP-5] - Incident Detail

- Research
    * [CYP-1] - Discover API

- Task
    * [CYP-2] - Update MI and REST


##### About this release

Version 1.0.2 (204) of Cyphort For Splunk  is compatible with:

| Item | Value |
| --- | --- |
| Splunk Enterprise versions | 6.2, 6.3, 6.4, 6.5 |
| CIM | 4.3 |
| Platforms |`<Platform independent>`  |
| Vendor Products | Cyphort API v3.3.0 |

##### New features

Cyphort For Splunk includes the following new features:

- Incident Overview
- Incident Details
- Application Health

##### Fixed issues

Version 1.0.2 (204) of Cyphort For Splunk fixes the following issues:

- No Fixed Issues. If you find an error, please contact Cyphort support.

##### Known issues

Version 1.0.2 (204) of Cyphort For Splunk has the following known issues:

- No Known Issues.

##### Support and resources

**Questions and answers**

Access questions and answers specific to Cyphort For Splunk at https://answers.splunk.com.

**Support**

Support Offered: Yes
Support URL: https://answers.splunk.com/app/questions/3061.html
Support Email: marketing@cyphort.com

Please visit the [Splunk Answers Ask Questions page](https://answers.splunk.com/answers/ask.html?appid=3061) to submit your question regarding Cyphort For Splunk. Please tag your question with the correct App tag (if not already tagged) and your question will be attended to.

## INSTALLATION AND CONFIGURATION

### Software requirements

To function properly, Cyphort For Splunk requires the following software:

- Splunk 6.2, 6.3, 6.4, 6.5
- Cyphort API v 3.3.0

### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements](http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

#### Download

Download Cyphort For Splunk at https://splunkbase.splunk.com/app/3061.

#### Installation steps

This app has the following inputs pre-configured:

None.

##### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1. Download the Cyphort For Splunk package from splunkbase.splunk.com.
1. Install the App via the recommended installation methods (CLI, Web GUI)
1. Restart Splunk.
1. Configure the Modular Input with the required settings.

##### Deploy to distributed deployment

**Install to search head**

1. Download the Cyphort For Splunk package from splunkbase.splunk.com.
1. Install the App via the recommended installation methods (CLI, Web GUI, Deployment Server)
1. Do NOT configure a Modular Input unless there is only 1 (one) single Search Head.

**Install to indexers**

1. Download the Cyphort For Splunk package from splunkbase.splunk.com.
1. Untar the package and locate the TA (Technology Add-On) located in "CyphortForSplunk/appserver/addons". The package will end in ".spl" and should be labeled "TA-CyphortForSplunk".
1. Install "TA-CyphortForSplunk" onto the indexers per your environment.

**Install to Universal Forwarders**

- There is no installation to Universal Forwarders.

**Install to Heavy Forwarders**

1. Download the Cyphort For Splunk package from splunkbase.splunk.com.
1. Untar the package and locate the IA (Input Add-On) located in "CyphortForSplunk/appserver/addons". The package will end in ".spl" and should be labeled "IA-CyphortForSplunk".
1. Install "IA-CyphortForSplunk" onto a heavy forwarder in your environment.
1. Configure the Modular Input with the required settings.

**Deploy to distributed deployment with Search Head Clustering**

1. Place the App into the "deploy_apps" folder on the Deployer Server.
2. Follow the instructions to install to a Heavy Forwarder. This Step is REQUIRED in a clustered SH environment!
3. Deploy the App to the Search Head Cluster. DO NOT install "IA-CyphortForSplunk" to the Cluster!

**Deploy to Splunk Cloud**

- Instruct the Splunk Cloud Support team to follow the instructions above that matches the Cloud environment.

**Summary**


## USER GUIDE

### Data types

This app provides the index-time and search-time knowledge for the following types of data from Cyphort:

- cyphort:api
    - This data feed is the result of the calls to the Cyphort API. If you aren't receiving incidents check here for a possible explanation.
- CyphortForSplunk:error
    - This data feed is the result of any errors presented during the consumption of Cyhport API data.
- cyphort:incident
    - This data feed is the output of the Incidents pulled from the Cyphort API data stream.

### Pre-Built Panels

Cyphort For Splunk uses pre-built panels on the Incident Overview dashboard. When cloning panels to new/existing dashboards make sure to use
the pre-built panels. Pre-built panels ensure that if a panel is removed and re-added to a dashboard (or if they are added to a new
dashboard) the panel will function as expected. As an example, panels on the incident overview drilldown to the incident detail dashboard.

Procedure to add existing panels to dashboards:

1. Select the `Edit` dropdown and choose `Edit Panels` from the menu.
2. Click the `+Add Panel` button.
3. Check under `Add Prebuilt Panel` to see if an appropriate panel already exists. If so, select this panel.
4. Create a new panel by clicking the `Add to Dashboard` button.
5. Click the `Done` button after the panel(s) have been added.

### Lookups

Cyphort For Splunk contains no lookup files.

### Event Generator

Cyphort For Splunk makes use of an event generator. This allows the product to display data when there are no inputs configured.

There are two samples to be used for event generation. These samples are found in the `samples` folder of the app.
- cyphort_incident.sample
- cyphort_event.sample

### Configure Cyphort For Splunk

- Install the App according to your environment (see steps above)
- Navigate to "Settings > Data Inputs > Cyphort For Splunk"

**Modular Input**

**NOTE:** You will need to configure a new modular input for each data source.

1. Navigate to `Settings` -> `Data Inputs`
2. Either click on "Cyphort For Splunk" and then the `New` button or the `Add New` link on the same row in the Actions column.
3. Enter the appropriate infomation in the following fields. Required fields have an asterisk (*) next to them.
 - *Name*: Descriptive name for the modular input
 - *Hostname*: FQDN of Cyphort appliance
 - *Token*: API token issued from the Cyphort appliance for authentication

 Note: Click the *More Settings* checkbox to expose the following options.

 - *Interval*: The number of seconds before running the command again or a valid cron schedule. Ensure that the `interval` setting is a minimum of 300 seconds.
 - *Set sourcetype*: Set to `Automatic` and should not be changed unless directed to by support.
 - *Host*: Set the hostname on the events with the entered value.
 - *Index*: The index setting must be changed to the index where the Cyphort data is to be stored. **Failure to change this setting from the default option will result in data being written to the *main* index**.
7. Press the `Next` button to save the configuration

### Troubleshoot Cyphort For Splunk

The best place to start troubleshooting Cyphort For Splunk is using the `App Health` dashboard under the `Administration` dropdown. There you will find several panels with information related to errors in the Cyphort For Splunk app.

Additionally the following search may be performed:

`eventtype = cyphort_error OR eventtype = cyphort_internal_error`

### Upgrade Cyphort For Splunk

Upgrade Cyphort For Splunk by re-installing into your environment per Splunk Documentation and your environment (see steps above).

### Dependencies

Cyphort For Splunk has dependencies and in this case are all-included within the App.

1. D3
1. jQuery
1. Markdown.js

### Knowledge Documentation
The following information is useful to know about how this app handles data.

1. Summary Indexing: No
1. Data Model Acceleration: No
1. Report Acceleration: No

### Third-party software attributions

Version 1.0.2 (204) of Cyphort For Splunk incorporates the following third-party software or libraries.

### Aplura, LLC Components
Components Written by Aplura, LLC
Copyright (C) 2016 Aplura, ,LLC

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, eMA  02110-1301, USA.
#### Vollkorn Font

Copyright (c) 2013, Friedrich Althausen (http://friedrichalthausen.de). All rights reserved.

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is copied below, and is also available with a FAQ at:
http://scripts.sil.org/OFL

SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded,
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply
to any document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may
include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical
writer or other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as stand-alone text files, human-readable headers or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless explicit written permission is granted by the corresponding
Copyright Holder. This restriction only applies to the primary font name as
presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any
Modified Version, except to acknowledge the contribution(s) of the
Copyright Holder(s) and the Author(s) or with their explicit written
permission.

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are
not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
OTHER DEALINGS IN THE FONT SOFTWARE.

#### markdown.js

Released under the MIT license.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
